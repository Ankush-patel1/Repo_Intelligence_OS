"""Verification script for automatic indexing integration."""

import ast
from pathlib import Path


def verify_imports():
    """Verify RepositoryIndexer and FileScanner are imported."""
    print("Checking imports...")
    
    file_path = Path("app/services/github/repository_service.py")
    content = file_path.read_text()
    
    required_imports = [
        "from app.services.indexing.file_scanner import FileScanner",
        "from app.services.indexing.repository_indexer import RepositoryIndexer",
    ]
    
    for required in required_imports:
        if required in content:
            print(f"  ✓ {required}")
        else:
            print(f"  ✗ MISSING: {required}")
            return False
    
    return True


def verify_indexer_calls():
    """Verify RepositoryIndexer is called in import and sync methods."""
    print("\nChecking indexer invocations...")
    
    file_path = Path("app/services/github/repository_service.py")
    content = file_path.read_text()
    tree = ast.parse(content)
    
    # Find the RepositoryService class
    repo_service = None
    for node in ast.walk(tree):
        if isinstance(node, ast.ClassDef) and node.name == "RepositoryService":
            repo_service = node
            break
    
    if not repo_service:
        print("  ✗ RepositoryService class not found")
        return False
    
    # Check import_repository method
    import_method = None
    sync_method = None
    
    for item in repo_service.body:
        if isinstance(item, ast.AsyncFunctionDef):
            if item.name == "import_repository":
                import_method = item
            elif item.name == "sync_repository":
                sync_method = item
    
    # Verify import_repository has indexer calls
    if import_method:
        method_source = ast.unparse(import_method)
        
        # Check for both paths (existing and new repository)
        indexer_calls = method_source.count("RepositoryIndexer")
        index_repo_calls = method_source.count("index_repository")
        
        if indexer_calls >= 2 and index_repo_calls >= 2:
            print(f"  ✓ import_repository: {indexer_calls} indexer instances, {index_repo_calls} index calls")
        else:
            print(f"  ✗ import_repository: Expected 2+ indexer calls, found {indexer_calls}")
            return False
    else:
        print("  ✗ import_repository method not found")
        return False
    
    # Verify sync_repository has indexer call
    if sync_method:
        method_source = ast.unparse(sync_method)
        
        if "RepositoryIndexer" in method_source and "index_repository" in method_source:
            print("  ✓ sync_repository: indexer call present")
        else:
            print("  ✗ sync_repository: indexer call missing")
            return False
    else:
        print("  ✗ sync_repository method not found")
        return False
    
    return True


def verify_indexer_placement():
    """Verify indexer is called after flush/refresh operations."""
    print("\nChecking indexer placement...")
    
    file_path = Path("app/services/github/repository_service.py")
    content = file_path.read_text()
    
    # Check import_repository method structure
    lines = content.split("\n")
    
    # Find import_repository method
    in_import_method = False
    found_pattern_1 = False  # refresh -> index pattern for existing repo
    found_pattern_2 = False  # refresh -> index pattern for new repo
    
    for i, line in enumerate(lines):
        if "async def import_repository" in line:
            in_import_method = True
        elif in_import_method and "async def " in line:
            in_import_method = False
        
        if in_import_method:
            # Check for pattern: refresh followed by indexer
            if "await self.session.refresh(existing)" in line:
                # Check next few lines for indexer
                for j in range(i + 1, min(i + 10, len(lines))):
                    if "RepositoryIndexer" in lines[j]:
                        found_pattern_1 = True
                        break
            
            if "await self.session.refresh(repository_model)" in line:
                # Check next few lines for indexer
                for j in range(i + 1, min(i + 10, len(lines))):
                    if "RepositoryIndexer" in lines[j]:
                        found_pattern_2 = True
                        break
    
    if found_pattern_1:
        print("  ✓ Indexer called after existing repository refresh")
    else:
        print("  ✗ Indexer not found after existing repository refresh")
    
    if found_pattern_2:
        print("  ✓ Indexer called after new repository refresh")
    else:
        print("  ✗ Indexer not found after new repository refresh")
    
    # Check sync_repository
    in_sync_method = False
    found_sync_pattern = False
    
    for i, line in enumerate(lines):
        if "async def sync_repository" in line:
            in_sync_method = True
        elif in_sync_method and "async def " in line:
            in_sync_method = False
        
        if in_sync_method:
            if "await self.session.refresh(repository)" in line:
                # Check next few lines for indexer
                for j in range(i + 1, min(i + 10, len(lines))):
                    if "RepositoryIndexer" in lines[j]:
                        found_sync_pattern = True
                        break
    
    if found_sync_pattern:
        print("  ✓ Indexer called after sync repository refresh")
    else:
        print("  ✗ Indexer not found after sync repository refresh")
    
    return found_pattern_1 and found_pattern_2 and found_sync_pattern


def main():
    """Run all verification checks."""
    print("=" * 60)
    print("Automatic Indexing Integration Verification")
    print("=" * 60)
    
    checks = [
        ("Imports", verify_imports),
        ("Indexer Calls", verify_indexer_calls),
        ("Indexer Placement", verify_indexer_placement),
    ]
    
    results = []
    for name, check_func in checks:
        try:
            result = check_func()
            results.append((name, result))
        except Exception as e:
            print(f"\n✗ {name} check failed with error: {e}")
            import traceback
            traceback.print_exc()
            results.append((name, False))
    
    print("\n" + "=" * 60)
    print("Summary:")
    print("=" * 60)
    
    for name, passed in results:
        status = "✓ PASS" if passed else "✗ FAIL"
        print(f"{name:20} {status}")
    
    print("=" * 60)
    
    if all(passed for _, passed in results):
        print("✓ ALL CHECKS PASSED")
        print("\nAutomatic indexing successfully integrated:")
        print("  - POST /repositories/import → auto-indexes")
        print("  - POST /repositories/{id}/sync → auto-indexes")
        return 0
    else:
        print("✗ SOME CHECKS FAILED")
        return 1


if __name__ == "__main__":
    exit(main())
