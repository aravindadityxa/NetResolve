# Alarm Correlation and Root Cause Analysis

## Overview

The correlation and RCA engines are the intelligent heart of NetResolve. They transform a flood of alarms into meaningful incidents with identified root causes.

## Architecture

```
Normalized Alarms (Kafka)
        ↓
┌───────────────────────────┐
│  Alarm Correlator         │
│  (Groups related alarms)  │
└───────────┬───────────────┘
            ↓
Correlation Groups
        ↓
┌───────────────────────────┐
│  RCA Analyzer             │
│  (Identifies root cause)  │
└───────────┬───────────────┘
            ↓
RCA Results with:
- Root cause alarm
- Confidence score
- Affected devices
- Remediation suggestions
```

## Part 1: Alarm Correlation

### Purpose

Groups related alarms that likely stem from the same fault.

**Input:** Individual alarms (e.g., 20 separate alarms from a cascade)
**Output:** Correlation groups (e.g., 1-3 groups of related alarms)

### Algorithm

**Multi-Signal Correlation Scoring:**

Each pair of alarms is scored across 5 dimensions:

```
Correlation Score = 
    (Temporal Score × 0.25) +
    (Topology Score × 0.25) +
    (Dependency Score × 0.25) +
    (Severity Score × 0.15) +
    (Type Score × 0.10)
= 0.0 to 1.0
```

#### 1. Temporal Proximity (0-1, weight 0.25)

**Rationale:** Alarms from same fault arrive within seconds/minutes.

Scoring:
```
Same second        → 1.0
< 10 seconds       → 0.8
< 60 seconds       → 0.5
< 5 minutes        → 0.2
> 5 minutes        → 0.0
```

#### 2. Topological Relationship (0-1, weight 0.25)

**Rationale:** Alarms on connected devices likely relate.

Scoring:
```
Same device         → 1.0
Adjacent devices    → 0.8
Same region/layer   → 0.5
Different regions   → 0.0
```

#### 3. Device Dependency (0-1, weight 0.25)

**Rationale:** Cascading failures follow upstream-to-downstream paths.

Scoring:
```
One upstream        → 0.9
Common upstream     → 0.7
Sibling devices     → 0.4
Independent        → 0.0
```

#### 4. Severity Correlation (0-1, weight 0.15)

**Rationale:** Related alarms often have similar severity.

Scoring:
```
Both critical       → 1.0
Same severity       → 0.8
Adjacent severity   → 0.5
Different severity  → 0.2
```

#### 5. Event Type Relationship (0-1, weight 0.10)

**Rationale:** Some alarm types are causally related.

Scoring:
```
Exact match         → 1.0
Related types       → 0.7
  (e.g., interface_down + device_unreachable)
Unrelated types     → 0.0
```

### Grouping Process

```
1. Sort alarms by timestamp (earliest first)
2. For each alarm:
   a. Calculate score against existing groups
   b. If score ≥ threshold (0.5):
      - Add to best-matching group
   c. Else:
      - Create new group
3. Return groups with statistics
```

### Example: Core Interface Failure

```
Alarms received:
  T+0s: CORE-R1 interface GigabitEthernet0/1 DOWN (severity: MAJOR)
  T+2s: DIST-R1 UNREACHABLE (severity: CRITICAL)
  T+3s: ACCESS-SW1 UNREACHABLE (severity: CRITICAL)
  T+4s: ACCESS-SW2 UNREACHABLE (severity: CRITICAL)

Correlation:

CORE-R1 ↔ DIST-R1:
  Temporal: 0.5 (2s apart, < 10s = 0.8) × 0.25
  Topology: 0.25 (adjacent) × 0.25
  Dependency: 0.225 (upstream) × 0.25
  Severity: 0.10 (MAJOR vs CRITICAL) × 0.15
  Type: 0.07 (interface_down vs device_unreachable) × 0.10
  Total: 0.56 → GROUP (above 0.5 threshold)

DIST-R1 ↔ ACCESS-SW1:
  Temporal: 0.2 (1s apart, < 5s)
  Topology: 0.25 (adjacent)
  Dependency: 0.225 (upstream)
  Severity: 0.0 (both CRITICAL)
  Type: 0.0 (same type)
  Total: 0.675 → GROUP

→ All 4 alarms in same correlation group
```

### Deduplication

Within correlation group, same device + alarm type → increment occurrence count instead of creating duplicate.

## Part 2: Root Cause Analysis

### Purpose

Identifies the primary fault from a correlation group.

**Input:** Correlated alarm group (1-N alarms)
**Output:** Root cause alarm with confidence and impact analysis

### Algorithm

**RCA Scoring:**

```
RCA Confidence =
    (Temporal Factor × 0.30) +
    (Topology Factor × 0.25) +
    (Cascade Factor × 0.25) +
    (Severity Factor × 0.20)
= 0.0 to 1.0
```

#### 1. Temporal Factor (0-1, weight 0.30)

**Question:** Is this the earliest alarm?

Scoring:
```
Earliest (0 delay)     → 1.0
Within 5 seconds        → 0.8
Within 30 seconds       → 0.5
Beyond 30 seconds       → 0.2
```

**Rationale:** Root causes appear first. Secondary alarms follow.

#### 2. Topology Factor (0-1, weight 0.25)

**Question:** Are all affected alarms downstream?

Scoring:
```
All downstream        → 1.0
80%+ downstream       → 0.8
50%+ downstream       → 0.6
25%+ downstream       → 0.3
None downstream       → 0.0
```

**Rationale:** Root cause device must be upstream of affected devices.

#### 3. Cascade Factor (0-1, weight 0.25)

**Question:** Do secondary alarms follow expected timing?

Scoring:
```
80%+ appear 0-120s after   → 1.0
50%+ appear 0-120s after   → 0.8
20%+ appear 0-120s after   → 0.5
Alarms before this one     → 0.1
```

**Rationale:** Cascades propagate downstream over time.

#### 4. Severity Factor (0-1, weight 0.20)

**Question:** Is severity appropriate for root cause?

Scoring:
```
CRITICAL or MAJOR   → 1.0
MINOR               → 0.7
WARNING             → 0.5
INFORMATIONAL       → 0.3
```

**Rationale:** Root causes typically have high severity.

### Root Cause Selection

```
1. Identify candidates:
   - Earliest alarm
   - Highest severity alarms
   - Primary failure types (device_unreachable, interface_down)

2. Score each candidate against entire group

3. Select candidate with highest confidence

4. Validate:
   - Calculate blast radius (affected devices)
   - Verify cascade pattern
   - Generate reasoning
```

### Example: Core Interface Failure Analysis

```
Correlation Group: [CORE-R1 iface down, DIST-R1 unreachable, 
                    ACCESS-SW1 unreachable, ACCESS-SW2 unreachable]

Candidates:
  A. CORE-R1 interface down (earliest, T+0s)
  B. DIST-R1 unreachable (T+2s)
  C. ACCESS-SW1 unreachable (T+3s)
  D. ACCESS-SW2 unreachable (T+4s)

Scoring Candidate A (CORE-R1):
  Temporal: 1.0 (earliest)        × 0.30 = 0.30
  Topology: 1.0 (all downstream)  × 0.25 = 0.25
  Cascade: 0.8 (3 after in 4s)    × 0.25 = 0.20
  Severity: 0.7 (MAJOR)           × 0.20 = 0.14
  Total: 0.89 ✓ SELECTED

Scoring Candidate B (DIST-R1):
  Temporal: 0.8 (2s after)        × 0.30 = 0.24
  Topology: 0.8 (2 downstream)    × 0.25 = 0.20
  Cascade: 0.5 (2 after in 2s)    × 0.25 = 0.125
  Severity: 1.0 (CRITICAL)        × 0.20 = 0.20
  Total: 0.745 (CORE-R1 still better)

→ Root Cause: CORE-R1 interface GigabitEthernet0/1
→ Confidence: 89%
→ Affected: [DIST-R1, ACCESS-SW1, ACCESS-SW2] (3 devices)
```

### Impact Calculation

**Blast Radius:**
- All devices downstream of root cause in topology
- Calculated using graph traversal

**Affected Devices:**
- All devices that generated alarms in the group
- Filtered to only downstream of root cause

**Services Impacted:**
- Derived from device types and roles

## Reasoning Engine

Generates human-readable explanations for RCA decisions.

### Evidence Presentation

```
Evidence:
  ✓ First event: Appeared first in sequence
  ✓ Upstream location: Located upstream of 3 affected devices
  ✓ Cascading pattern: 3 secondary alarms followed
  ✓ High severity: MAJOR severity consistent with root cause

Impact:
  Directly affected: 3 devices
    - DIST-R1
    - ACCESS-SW1
    - ACCESS-SW2

Confidence: 89%
  Note: High confidence. This is the most likely root cause.
```

### Remediation Suggestions

Auto-generated based on alarm type:

**Interface Down:**
- Check physical connection
- Verify cable and port status
- Run interface diagnostics
- Perform shutdown/no-shutdown cycle

**Device Unreachable:**
- Verify management connectivity
- Check device power/boot status
- Attempt SSH/telnet
- Check routing to management network

**High Latency:**
- Check interface utilization
- Verify QoS policies
- Check upstream congestion
- Verify routing convergence

## Usage Examples

### Via Python

```python
from sqlalchemy.orm import Session
from app.correlation import AlarmCorrelator
from app.rca import RCAAnalyzer

db = Session()

# 1. Correlate alarms
correlator = AlarmCorrelator(db)
groups = correlator.correlate_alarms()

for group in groups:
    print(f"Group {group['correlation_id']}: {group['alarm_count']} alarms")
    print(f"  Average score: {group['average_score']:.3f}")

# 2. Perform RCA on each group
analyzer = RCAAnalyzer(db)
for group in groups:
    rca = analyzer.analyze_correlation_group(group['correlation_id'])
    print(f"Root cause: {rca['root_cause_device_hostname']}")
    print(f"Confidence: {rca['confidence']:.1%}")
    print(f"Affected: {rca['blast_radius']} devices")
    print(rca['reasoning'])
```

### Via REST API (Phase 10)

```bash
# Get correlation groups
curl http://localhost:8000/api/correlation/groups

# Get group details
curl http://localhost:8000/api/correlation/{correlation_id}

# Run RCA on group
curl -X POST http://localhost:8000/api/rca/{correlation_id}/analyze
```

## Tuning Parameters

In `app/core/constants.py`:

```python
# Correlation threshold (0-1, default 0.5)
CORRELATION_SCORE_THRESHOLD = 0.5
# Higher = stricter grouping, more groups
# Lower = looser grouping, fewer groups

# RCA confidence threshold (0-1, default 0.65)
RCA_CONFIDENCE_THRESHOLD = 0.65
# Higher = only confident RCA results
# Lower = accept lower-confidence results

# Deduplication window (seconds, default 300)
ALARM_DEDUP_WINDOW_SECONDS = 300
# Time window for considering alarms as duplicates
```

## Accuracy and Limitations

### Accuracy Factors

✓ **Accurate when:**
- Clear primary failure followed by cascades
- Topology model is up-to-date
- Timestamp precision is good (± 5 seconds)
- Alarms follow expected patterns

✗ **Inaccurate when:**
- Multiple independent failures occur simultaneously
- Topology model is stale or incorrect
- Alarms are heavily delayed or out-of-order
- Unusual failure patterns (e.g., single alarm on core device)

### False Positives/Negatives

**False Positives:** Incorrectly identified as related
- Mitigation: Increase correlation threshold
- Impact: More groups to analyze

**False Negatives:** Missed relationships
- Mitigation: Decrease correlation threshold
- Impact: Fewer groups, potentially missing details

## Performance

**Single Correlation Group:** ~10-50ms
**RCA per Group:** ~50-200ms
**Batch of 100 groups:** ~5-15 seconds

**Bottlenecks:**
- Database queries for topology
- Graph traversal for blast radius
- Pairwise scoring calculation

**Optimizations:**
- Cache topology graph
- Batch topology queries
- Vectorize scoring

## Integrations

### With Suppression Engine (Phase 8)
- RCA identifies root cause alarm
- Suppression marks other alarms in group as secondary
- Only root cause is visible to operators

### With Incident Manager (Phase 9)
- One incident created per correlation group
- RCA results populate incident fields
- Reasoning becomes incident description

### With Dashboard (Phase 11)
- Confidence score displayed as percentage
- Affected devices highlighted on topology
- Reasoning shown in incident detail

## Next Phase

Phase 8: Alarm Suppression Engine - Hides secondary alarms to reduce noise.
