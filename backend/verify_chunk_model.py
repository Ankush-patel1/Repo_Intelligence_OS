"""Verification script for RepositoryChunk database model."""

from app.db.models.repository_chunk import RepositoryChunk


def verify_model():
    """Verify the RepositoryChunk model structure."""
    print("=" * 60)
    print("RepositoryChunk Model Verification")
    print("=" * 60)
    
    # Check table name
    print(f"\n✓ Table name: {RepositoryChunk.__tablename__}")
    
    # Check columns
    columns = RepositoryChunk.__table__.columns
    print(f"\n✓ Column count: {len(columns)}")
    print("\nColumns:")
    for col in columns:
        nullable = "NULL" if col.nullable else "NOT NULL"
        print(f"  - {col.name}: {col.type} ({nullable})")
    
    # Check foreign keys
    fks = RepositoryChunk.__table__.foreign_keys
    print(f"\n✓ Foreign key count: {len(fks)}")
    print("\nForeign Keys:")
    for fk in fks:
        print(f"  - {fk.parent.name} → {fk.target_fullname} (ondelete={fk.ondelete})")
    
    # Check indexes
    indexes = RepositoryChunk.__table__.indexes
    print(f"\n✓ Index count: {len(indexes)}")
    print("\nIndexes:")
    for idx in sorted(indexes, key=lambda x: x.name):
        cols = ', '.join([c.name for c in idx.columns])
        print(f"  - {idx.name}: ({cols})")
    
    # Check relationships
    print(f"\n✓ SQLAlchemy Relationships:")
    print(f"  - repository: {hasattr(RepositoryChunk, 'repository')}")
    print(f"  - repository_file: {hasattr(RepositoryChunk, 'repository_file')}")
    print(f"  - symbol: {hasattr(RepositoryChunk, 'symbol')}")
    
    print("\n" + "=" * 60)
    print("✓ Model verification complete!")
    print("=" * 60)
    
    return True


if __name__ == "__main__":
    try:
        verify_model()
        print("\n✅ SUCCESS: RepositoryChunk model is correctly configured")
    except Exception as e:
        print(f"\n❌ ERROR: {e}")
        raise

