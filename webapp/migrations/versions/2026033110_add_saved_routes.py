"""Add saved routes

Revision ID: 4cc7f9f6d5a1
Revises: 16e4c4bc2be0
Create Date: 2026-03-31 10:00:00.000000

"""

import sqlalchemy as sa
from alembic import op

# Revision identifiers - used by alembic
revision = "4cc7f9f6d5a1"
down_revision = "16e4c4bc2be0"
branch_labels = None
depends_on = None


def upgrade():
    op.create_table(
        "saved_routes",
        sa.Column("user_id", sa.Integer(), nullable=False),
        sa.Column("name", sa.String(length=256), nullable=False),
        sa.Column("start_name", sa.String(length=256), nullable=False),
        sa.Column("start_lat", sa.Double(), nullable=False),
        sa.Column("start_lon", sa.Double(), nullable=False),
        sa.Column("end_name", sa.String(length=256), nullable=False),
        sa.Column("end_lat", sa.Double(), nullable=False),
        sa.Column("end_lon", sa.Double(), nullable=False),
        sa.Column("stops", sa.JSON(), nullable=False),
        sa.Column("route_geojson", sa.JSON(), nullable=False),
        sa.Column("total_distance_miles", sa.Double(), nullable=False),
        sa.Column("total_duration_minutes", sa.Integer(), nullable=False),
        sa.Column(
            "created_date",
            sa.DateTime(),
            server_default=sa.text("CURRENT_TIMESTAMP"),
            nullable=False,
        ),
        sa.Column(
            "modified_date",
            sa.DateTime(),
            server_default=sa.text("CURRENT_TIMESTAMP"),
            nullable=False,
        ),
        sa.Column("id", sa.Integer(), autoincrement=True, nullable=False),
        sa.ForeignKeyConstraint(
            ["user_id"], ["users.id"], name=op.f("fk_saved_routes_user_id_users")
        ),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_saved_routes")),
    )
    op.create_index(op.f("ix_saved_routes_user_id"), "saved_routes", ["user_id"], unique=False)


def downgrade():
    op.drop_index(op.f("ix_saved_routes_user_id"), table_name="saved_routes")
    op.drop_table("saved_routes")
