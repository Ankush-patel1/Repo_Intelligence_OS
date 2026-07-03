"""create knowledge graph tables

Revision ID: 20260703_1500_create_knowledge_graph_tables
Revises: 20260703_0001_create_repository_symbols
Create Date: 2026-07-03 15:00:00.000000

"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql


# revision identifiers, used by Alembic.
revision = '20260703_1500_create_knowledge_graph_tables'
down_revision = '20260703_0001_create_repository_symbols'
branch_labels = None
depends_on = None


def upgrade() -> None:
    # Create repository_nodes table
    op.create_table(
        'repository_nodes',
        sa.Column('id', postgresql.UUID(as_uuid=True), server_default=sa.text('gen_random_uuid()'), nullable=False, comment='Unique identifier for the node'),
        sa.Column('repository_id', postgresql.UUID(as_uuid=True), nullable=False, comment='Reference to the repository this node belongs to'),
        sa.Column('repository_file_id', postgresql.UUID(as_uuid=True), nullable=True, comment='Reference to file (if node represents a file or symbol in a file)'),
        sa.Column('symbol_id', postgresql.UUID(as_uuid=True), nullable=True, comment='Reference to symbol (if node represents a code symbol)'),
        sa.Column('node_type', sa.String(length=64), nullable=False, comment='Type of node: repository, file, module, symbol'),
        sa.Column('display_name', sa.String(length=512), nullable=False, comment='Human-readable name for the node'),
        sa.Column('language', sa.String(length=32), nullable=True, comment='Programming language (for file and symbol nodes)'),
        sa.Column('metadata', sa.Text(), nullable=True, comment='JSON metadata for the node (type-specific properties)'),
        sa.Column('created_at', sa.DateTime(), server_default=sa.text('now()'), nullable=False, comment='Timestamp when the node was created'),
        sa.ForeignKeyConstraint(['repository_id'], ['repositories.id'], ondelete='CASCADE'),
        sa.ForeignKeyConstraint(['repository_file_id'], ['repository_files.id'], ondelete='CASCADE'),
        sa.ForeignKeyConstraint(['symbol_id'], ['repository_symbols.id'], ondelete='CASCADE'),
        sa.PrimaryKeyConstraint('id')
    )
    
    # Create indexes for repository_nodes
    op.create_index('ix_repository_nodes_repository_id', 'repository_nodes', ['repository_id'], unique=False)
    op.create_index('ix_repository_nodes_repository_file_id', 'repository_nodes', ['repository_file_id'], unique=False)
    op.create_index('ix_repository_nodes_symbol_id', 'repository_nodes', ['symbol_id'], unique=False)
    op.create_index('ix_repository_nodes_node_type', 'repository_nodes', ['node_type'], unique=False)
    op.create_index('ix_repository_nodes_display_name', 'repository_nodes', ['display_name'], unique=False)
    op.create_index('ix_repository_nodes_language', 'repository_nodes', ['language'], unique=False)
    op.create_index('ix_repository_nodes_repository_id_node_type', 'repository_nodes', ['repository_id', 'node_type'], unique=False)
    op.create_index('ix_repository_nodes_repository_id_language', 'repository_nodes', ['repository_id', 'language'], unique=False)
    op.create_index('ix_repository_nodes_symbol_id_node_type', 'repository_nodes', ['symbol_id', 'node_type'], unique=False)

    # Create repository_edges table
    op.create_table(
        'repository_edges',
        sa.Column('id', postgresql.UUID(as_uuid=True), server_default=sa.text('gen_random_uuid()'), nullable=False, comment='Unique identifier for the edge'),
        sa.Column('source_node_id', postgresql.UUID(as_uuid=True), nullable=False, comment='Reference to the source node of this relationship'),
        sa.Column('target_node_id', postgresql.UUID(as_uuid=True), nullable=False, comment='Reference to the target node of this relationship'),
        sa.Column('relationship_type', sa.String(length=64), nullable=False, comment='Type of relationship (IMPORTS, CALLS, INHERITS, REFERENCES, etc.)'),
        sa.Column('metadata', sa.Text(), nullable=True, comment='JSON metadata for the edge (relationship-specific properties)'),
        sa.Column('created_at', sa.DateTime(), server_default=sa.text('now()'), nullable=False, comment='Timestamp when the edge was created'),
        sa.ForeignKeyConstraint(['source_node_id'], ['repository_nodes.id'], ondelete='CASCADE'),
        sa.ForeignKeyConstraint(['target_node_id'], ['repository_nodes.id'], ondelete='CASCADE'),
        sa.PrimaryKeyConstraint('id')
    )
    
    # Create indexes for repository_edges
    op.create_index('ix_repository_edges_source_node_id', 'repository_edges', ['source_node_id'], unique=False)
    op.create_index('ix_repository_edges_target_node_id', 'repository_edges', ['target_node_id'], unique=False)
    op.create_index('ix_repository_edges_relationship_type', 'repository_edges', ['relationship_type'], unique=False)
    op.create_index('ix_repository_edges_source_node_id_relationship_type', 'repository_edges', ['source_node_id', 'relationship_type'], unique=False)
    op.create_index('ix_repository_edges_target_node_id_relationship_type', 'repository_edges', ['target_node_id', 'relationship_type'], unique=False)
    op.create_index('ix_repository_edges_source_target', 'repository_edges', ['source_node_id', 'target_node_id'], unique=False)
    op.create_index('ix_repository_edges_relationship_type_created_at', 'repository_edges', ['relationship_type', 'created_at'], unique=False)


def downgrade() -> None:
    # Drop indexes for repository_edges
    op.drop_index('ix_repository_edges_relationship_type_created_at', table_name='repository_edges')
    op.drop_index('ix_repository_edges_source_target', table_name='repository_edges')
    op.drop_index('ix_repository_edges_target_node_id_relationship_type', table_name='repository_edges')
    op.drop_index('ix_repository_edges_source_node_id_relationship_type', table_name='repository_edges')
    op.drop_index('ix_repository_edges_relationship_type', table_name='repository_edges')
    op.drop_index('ix_repository_edges_target_node_id', table_name='repository_edges')
    op.drop_index('ix_repository_edges_source_node_id', table_name='repository_edges')
    
    # Drop repository_edges table
    op.drop_table('repository_edges')
    
    # Drop indexes for repository_nodes
    op.drop_index('ix_repository_nodes_symbol_id_node_type', table_name='repository_nodes')
    op.drop_index('ix_repository_nodes_repository_id_language', table_name='repository_nodes')
    op.drop_index('ix_repository_nodes_repository_id_node_type', table_name='repository_nodes')
    op.drop_index('ix_repository_nodes_language', table_name='repository_nodes')
    op.drop_index('ix_repository_nodes_display_name', table_name='repository_nodes')
    op.drop_index('ix_repository_nodes_node_type', table_name='repository_nodes')
    op.drop_index('ix_repository_nodes_symbol_id', table_name='repository_nodes')
    op.drop_index('ix_repository_nodes_repository_file_id', table_name='repository_nodes')
    op.drop_index('ix_repository_nodes_repository_id', table_name='repository_nodes')
    
    # Drop repository_nodes table
    op.drop_table('repository_nodes')
