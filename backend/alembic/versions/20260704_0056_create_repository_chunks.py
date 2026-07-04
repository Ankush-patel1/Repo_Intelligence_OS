"""create repository chunks table

Revision ID: 20260704_0056
Revises: 20260703_1500
Create Date: 2026-07-04 00:56:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision: str = '20260704_0056'
down_revision: Union[str, None] = '20260703_1500_create_knowledge_graph_tables'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Create repository_chunks table for semantic code chunking."""
    # Create repository_chunks table
    op.create_table(
        'repository_chunks',
        sa.Column('id', sa.UUID(), server_default=sa.text('gen_random_uuid()'), nullable=False, comment='Unique identifier for the chunk'),
        sa.Column('repository_id', sa.UUID(), nullable=False, comment='Reference to the repository this chunk belongs to'),
        sa.Column('repository_file_id', sa.UUID(), nullable=True, comment='Reference to the file this chunk is from (if applicable)'),
        sa.Column('symbol_id', sa.UUID(), nullable=True, comment='Reference to the symbol this chunk represents (if applicable)'),
        sa.Column('chunk_type', sa.String(length=64), nullable=False, comment='Type of chunk: function, method, class, imports, interface, test, documentation, configuration'),
        sa.Column('chunk_name', sa.String(length=512), nullable=False, comment='Human-readable name for the chunk (function name, class name, etc.)'),
        sa.Column('language', sa.String(length=32), nullable=False, comment='Programming language of the chunk'),
        sa.Column('content', sa.Text(), nullable=False, comment='The actual chunk content (code with context)'),
        sa.Column('metadata', sa.Text(), nullable=True, comment='JSON metadata for the chunk (type-specific properties, context info, relationships)'),
        sa.Column('token_count', sa.BigInteger(), nullable=False, comment='Approximate token count for the chunk (for LLM processing)'),
        sa.Column('content_hash', sa.String(length=64), nullable=False, comment='SHA256 hash of content for deduplication'),
        sa.Column('created_at', sa.DateTime(), server_default=sa.text('now()'), nullable=False, comment='Timestamp when the chunk was created'),
        sa.ForeignKeyConstraint(['repository_id'], ['repositories.id'], ondelete='CASCADE'),
        sa.ForeignKeyConstraint(['repository_file_id'], ['repository_files.id'], ondelete='CASCADE'),
        sa.ForeignKeyConstraint(['symbol_id'], ['repository_symbols.id'], ondelete='CASCADE'),
        sa.PrimaryKeyConstraint('id')
    )
    
    # Create indexes
    op.create_index('ix_repository_chunks_repository_id', 'repository_chunks', ['repository_id'], unique=False)
    op.create_index('ix_repository_chunks_repository_file_id', 'repository_chunks', ['repository_file_id'], unique=False)
    op.create_index('ix_repository_chunks_symbol_id', 'repository_chunks', ['symbol_id'], unique=False)
    op.create_index('ix_repository_chunks_chunk_type', 'repository_chunks', ['chunk_type'], unique=False)
    op.create_index('ix_repository_chunks_chunk_name', 'repository_chunks', ['chunk_name'], unique=False)
    op.create_index('ix_repository_chunks_language', 'repository_chunks', ['language'], unique=False)
    op.create_index('ix_repository_chunks_token_count', 'repository_chunks', ['token_count'], unique=False)
    op.create_index('ix_repository_chunks_content_hash', 'repository_chunks', ['content_hash'], unique=False)
    op.create_index('ix_repository_chunks_created_at', 'repository_chunks', ['created_at'], unique=False)
    
    # Create composite indexes for common query patterns
    op.create_index('ix_repository_chunks_repository_id_chunk_type', 'repository_chunks', ['repository_id', 'chunk_type'], unique=False)
    op.create_index('ix_repository_chunks_repository_id_language', 'repository_chunks', ['repository_id', 'language'], unique=False)
    op.create_index('ix_repository_chunks_file_id_chunk_type', 'repository_chunks', ['repository_file_id', 'chunk_type'], unique=False)
    op.create_index('ix_repository_chunks_language_chunk_type', 'repository_chunks', ['language', 'chunk_type'], unique=False)


def downgrade() -> None:
    """Drop repository_chunks table."""
    # Drop indexes first
    op.drop_index('ix_repository_chunks_language_chunk_type', table_name='repository_chunks')
    op.drop_index('ix_repository_chunks_file_id_chunk_type', table_name='repository_chunks')
    op.drop_index('ix_repository_chunks_repository_id_language', table_name='repository_chunks')
    op.drop_index('ix_repository_chunks_repository_id_chunk_type', table_name='repository_chunks')
    op.drop_index('ix_repository_chunks_created_at', table_name='repository_chunks')
    op.drop_index('ix_repository_chunks_content_hash', table_name='repository_chunks')
    op.drop_index('ix_repository_chunks_token_count', table_name='repository_chunks')
    op.drop_index('ix_repository_chunks_language', table_name='repository_chunks')
    op.drop_index('ix_repository_chunks_chunk_name', table_name='repository_chunks')
    op.drop_index('ix_repository_chunks_chunk_type', table_name='repository_chunks')
    op.drop_index('ix_repository_chunks_symbol_id', table_name='repository_chunks')
    op.drop_index('ix_repository_chunks_repository_file_id', table_name='repository_chunks')
    op.drop_index('ix_repository_chunks_repository_id', table_name='repository_chunks')
    
    # Drop table
    op.drop_table('repository_chunks')

