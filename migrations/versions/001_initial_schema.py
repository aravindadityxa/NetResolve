"""Initial schema creation

Revision ID: 001
Revises:
Create Date: 2024-01-01 00:00:00.000000

"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision = "001"
down_revision = None
branch_labels = None
depends_on = None


def upgrade() -> None:
    """Create initial schema."""
    # Create devices table
    op.create_table(
        "devices",
        sa.Column("id", sa.String(36), nullable=False),
        sa.Column("hostname", sa.String(255), nullable=False),
        sa.Column("device_type", sa.Enum("core_router", "distribution_router", "access_switch", "edge_router", "aggregation_switch", "host", "firewall", "load_balancer", name="devicetype"), nullable=False),
        sa.Column("ip_address", sa.String(45), nullable=False),
        sa.Column("status", sa.String(50), nullable=False, server_default="up"),
        sa.Column("description", sa.String(500)),
        sa.Column("created_at", sa.DateTime(), nullable=False),
        sa.Column("updated_at", sa.DateTime(), nullable=False),
        sa.Column("last_seen", sa.DateTime(), nullable=False),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("hostname"),
    )
    op.create_index(op.f("ix_devices_hostname"), "devices", ["hostname"], unique=True)

    # Create interfaces table
    op.create_table(
        "interfaces",
        sa.Column("id", sa.String(36), nullable=False),
        sa.Column("name", sa.String(255), nullable=False),
        sa.Column("device_id", sa.String(36), nullable=False),
        sa.Column("interface_type", sa.Enum("gigabit_ethernet", "ten_gigabit_ethernet", "serial", "virtual", "loopback", name="interfacetype"), nullable=False),
        sa.Column("status", sa.String(50), nullable=False, server_default="up"),
        sa.Column("speed_mbps", sa.Integer()),
        sa.Column("mtu", sa.Integer(), nullable=False, server_default="1500"),
        sa.Column("ip_address", sa.String(45)),
        sa.Column("description", sa.String(500)),
        sa.Column("created_at", sa.DateTime(), nullable=False),
        sa.Column("updated_at", sa.DateTime(), nullable=False),
        sa.ForeignKeyConstraint(["device_id"], ["devices.id"], ),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(op.f("ix_interfaces_device_id"), "interfaces", ["device_id"])

    # Create links table
    op.create_table(
        "links",
        sa.Column("id", sa.String(36), nullable=False),
        sa.Column("source_interface_id", sa.String(36), nullable=False),
        sa.Column("target_interface_id", sa.String(36), nullable=False),
        sa.Column("status", sa.String(50), nullable=False, server_default="up"),
        sa.Column("created_at", sa.DateTime(), nullable=False),
        sa.Column("updated_at", sa.DateTime(), nullable=False),
        sa.ForeignKeyConstraint(["source_interface_id"], ["interfaces.id"], ),
        sa.ForeignKeyConstraint(["target_interface_id"], ["interfaces.id"], ),
        sa.PrimaryKeyConstraint("id"),
    )

    # Create network_events table
    op.create_table(
        "network_events",
        sa.Column("id", sa.String(36), nullable=False),
        sa.Column("event_id", sa.String(255), nullable=False),
        sa.Column("timestamp", sa.DateTime(), nullable=False),
        sa.Column("source", sa.String(100), nullable=False),
        sa.Column("device_id", sa.String(36), nullable=False),
        sa.Column("device_hostname", sa.String(255), nullable=False),
        sa.Column("event_type", sa.String(100), nullable=False),
        sa.Column("interface_id", sa.String(36)),
        sa.Column("severity", sa.String(50), nullable=False, server_default="informational"),
        sa.Column("message", sa.Text(), nullable=False),
        sa.Column("raw_data", sa.JSON()),
        sa.Column("created_at", sa.DateTime(), nullable=False),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("event_id"),
    )
    op.create_index(op.f("ix_network_events_timestamp"), "network_events", ["timestamp"])
    op.create_index(op.f("ix_network_events_source"), "network_events", ["source"])
    op.create_index(op.f("ix_network_events_device_id"), "network_events", ["device_id"])
    op.create_index(op.f("ix_network_events_event_type"), "network_events", ["event_type"])
    op.create_index(op.f("ix_network_events_created_at"), "network_events", ["created_at"])

    # Create alarms table
    op.create_table(
        "alarms",
        sa.Column("id", sa.String(36), nullable=False),
        sa.Column("event_id", sa.String(255), nullable=False),
        sa.Column("timestamp", sa.DateTime(), nullable=False),
        sa.Column("device_id", sa.String(36), nullable=False),
        sa.Column("device_hostname", sa.String(255), nullable=False),
        sa.Column("interface_id", sa.String(36)),
        sa.Column("alarm_type", sa.Enum("interface_down", "interface_degraded", "device_unreachable", "high_latency", "packet_loss", "link_flapping", "device_recovery", "interface_recovery", "dependency_failure", name="alarmtype"), nullable=False),
        sa.Column("severity", sa.Enum("critical", "major", "minor", "warning", "informational", "debug", name="alarmseverity"), nullable=False),
        sa.Column("status", sa.Enum("open", "acknowledged", "suppressed", "resolved", "cleared", name="alarmstatus"), nullable=False, server_default="open"),
        sa.Column("message", sa.Text(), nullable=False),
        sa.Column("source", sa.String(100), nullable=False),
        sa.Column("correlation_id", sa.String(36)),
        sa.Column("parent_alarm_id", sa.String(36)),
        sa.Column("probable_root_cause", sa.Boolean()),
        sa.Column("confidence", sa.Float()),
        sa.Column("first_seen", sa.DateTime(), nullable=False),
        sa.Column("last_seen", sa.DateTime(), nullable=False),
        sa.Column("occurrence_count", sa.Integer(), nullable=False, server_default="1"),
        sa.Column("raw_data", sa.JSON()),
        sa.Column("created_at", sa.DateTime(), nullable=False),
        sa.Column("updated_at", sa.DateTime(), nullable=False),
        sa.ForeignKeyConstraint(["device_id"], ["devices.id"], ),
        sa.ForeignKeyConstraint(["interface_id"], ["interfaces.id"], ),
        sa.ForeignKeyConstraint(["parent_alarm_id"], ["alarms.id"], ),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("event_id"),
    )
    op.create_index(op.f("ix_alarms_timestamp"), "alarms", ["timestamp"])
    op.create_index(op.f("ix_alarms_device_id"), "alarms", ["device_id"])
    op.create_index(op.f("ix_alarms_alarm_type"), "alarms", ["alarm_type"])
    op.create_index(op.f("ix_alarms_status"), "alarms", ["status"])
    op.create_index(op.f("ix_alarms_correlation_id"), "alarms", ["correlation_id"])

    # Create incidents table
    op.create_table(
        "incidents",
        sa.Column("id", sa.String(36), nullable=False),
        sa.Column("state", sa.Enum("open", "correlated", "root_cause_identified", "active", "recovering", "resolved", name="incidentstate"), nullable=False, server_default="open"),
        sa.Column("severity", sa.String(50), nullable=False),
        sa.Column("created_at", sa.DateTime(), nullable=False),
        sa.Column("updated_at", sa.DateTime(), nullable=False),
        sa.Column("resolved_at", sa.DateTime()),
        sa.Column("root_cause_device_id", sa.String(36)),
        sa.Column("root_cause_interface_id", sa.String(36)),
        sa.Column("root_cause_alarm_id", sa.String(36)),
        sa.Column("probable_root_cause", sa.Text()),
        sa.Column("rca_confidence", sa.Float()),
        sa.Column("rca_reasoning", sa.Text()),
        sa.Column("blast_radius", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("affected_links", sa.JSON()),
        sa.Column("timeline_data", sa.JSON()),
        sa.Column("suppression_count", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("mttd", sa.Float()),
        sa.Column("mtti", sa.Float()),
        sa.Column("mttr", sa.Float()),
        sa.Column("extra_metadata", sa.JSON()),
        sa.ForeignKeyConstraint(["root_cause_device_id"], ["devices.id"], ),
        sa.ForeignKeyConstraint(["root_cause_alarm_id"], ["alarms.id"], ),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(op.f("ix_incidents_state"), "incidents", ["state"])
    op.create_index(op.f("ix_incidents_created_at"), "incidents", ["created_at"])

    # Create incident_alarms association table
    op.create_table(
        "incident_alarms",
        sa.Column("id", sa.String(36), nullable=False),
        sa.Column("incident_id", sa.String(36), nullable=False),
        sa.Column("alarm_id", sa.String(36), nullable=False),
        sa.Column("is_suppressed", sa.Boolean(), nullable=False, server_default="0"),
        sa.Column("suppression_reason", sa.Text()),
        sa.Column("created_at", sa.DateTime(), nullable=False),
        sa.ForeignKeyConstraint(["alarm_id"], ["alarms.id"], ),
        sa.ForeignKeyConstraint(["incident_id"], ["incidents.id"], ),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(op.f("ix_incident_alarms_incident_id"), "incident_alarms", ["incident_id"])

    # Create timeline_events table
    op.create_table(
        "timeline_events",
        sa.Column("id", sa.String(36), nullable=False),
        sa.Column("incident_id", sa.String(36), nullable=False),
        sa.Column("timestamp", sa.DateTime(), nullable=False),
        sa.Column("device_id", sa.String(36)),
        sa.Column("device_hostname", sa.String(255)),
        sa.Column("event_type", sa.String(100), nullable=False),
        sa.Column("message", sa.Text(), nullable=False),
        sa.Column("alarm_id", sa.String(36)),
        sa.Column("created_at", sa.DateTime(), nullable=False),
        sa.ForeignKeyConstraint(["device_id"], ["devices.id"], ),
        sa.ForeignKeyConstraint(["incident_id"], ["incidents.id"], ),
        sa.ForeignKeyConstraint(["alarm_id"], ["alarms.id"], ),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(op.f("ix_timeline_events_incident_id"), "timeline_events", ["incident_id"])

    # Create topology_snapshots table
    op.create_table(
        "topology_snapshots",
        sa.Column("id", sa.String(36), nullable=False),
        sa.Column("timestamp", sa.DateTime(), nullable=False),
        sa.Column("devices", sa.JSON(), nullable=False),
        sa.Column("links", sa.JSON(), nullable=False),
        sa.Column("interfaces", sa.JSON(), nullable=False),
        sa.Column("dependencies", sa.JSON()),
        sa.Column("created_at", sa.DateTime(), nullable=False),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(op.f("ix_topology_snapshots_timestamp"), "topology_snapshots", ["timestamp"])


def downgrade() -> None:
    """Drop all tables."""
    op.drop_table("topology_snapshots")
    op.drop_table("timeline_events")
    op.drop_table("incident_alarms")
    op.drop_table("incidents")
    op.drop_table("alarms")
    op.drop_table("network_events")
    op.drop_table("links")
    op.drop_table("interfaces")
    op.drop_table("devices")
