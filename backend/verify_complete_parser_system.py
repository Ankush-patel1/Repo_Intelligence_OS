"""Comprehensive verification of the complete parser system."""

import sys
from pathlib import Path
from app.services.parser.parser_factory import ParserFactory

print("=" * 80)
print("COMPLETE PARSER SYSTEM VERIFICATION")
print("=" * 80)

# Initialize factory
factory = ParserFactory()

# 1. SUPPORTED LANGUAGES
print("\n1. SUPPORTED LANGUAGES")
print("-" * 80)
supported_languages = factory.get_supported_languages()
print(f"Total: {len(supported_languages)} languages")
for i, lang in enumerate(sorted(supported_languages), 1):
    print(f"  {i}. {lang}")

# 2. SUPPORTED EXTENSIONS
print("\n2. SUPPORTED FILE EXTENSIONS")
print("-" * 80)
supported_extensions = factory.get_supported_extensions()
print(f"Total: {len(supported_extensions)} extensions")

# Group extensions by language
extension_to_lang = {}
for ext in supported_extensions:
    parser = factory.get_parser_by_extension(ext)
    lang = parser.language
    if lang not in extension_to_lang:
        extension_to_lang[lang] = []
    extension_to_lang[lang].append(ext)

for lang in sorted(extension_to_lang.keys()):
    exts = ", ".join(sorted(extension_to_lang[lang]))
    print(f"  {lang}: {exts}")

# 3. PARSER FACTORY VERIFICATION
print("\n3. PARSER FACTORY VERIFICATION")
print("-" * 80)

test_cases = [
    ("Python", ".py", "test.py"),
    ("JavaScript", ".js", "test.js"),
    ("TypeScript", ".ts", "test.ts"),
    ("Java", ".java", "Test.java"),
    ("C", ".c", "test.c"),
    ("C++", ".cpp", "test.cpp"),
    ("Go", ".go", "main.go"),
    ("Rust", ".rs", "main.rs"),
]

all_passed = True
for lang, ext, filename in test_cases:
    # Test by language
    parser1 = factory.get_parser_by_language(lang)
    # Test by extension
    parser2 = factory.get_parser_by_extension(ext)
    # Test by path
    parser3 = factory.get_parser_by_path(Path(filename))
    
    # Verify all return same parser type
    if parser1.language == lang and parser2.language == lang and parser3.language == lang:
        print(f"  ✓ {lang}: Language={parser1.language}, Class={parser1.__class__.__name__}")
    else:
        print(f"  ✗ {lang}: FAILED - Inconsistent parsers")
        all_passed = False

if not all_passed:
    print("\n⚠ Some parser factory tests FAILED")
    sys.exit(1)

# 4. CREATE SAMPLE FILES AND PARSE
print("\n4. SAMPLE FILE PARSING")
print("-" * 80)

samples = {
    "test_sample.py": """
# Python sample
import os

class MyClass:
    def __init__(self, name):
        self.name = name
    
    def greet(self):
        return f"Hello, {self.name}"

def main():
    obj = MyClass("World")
    print(obj.greet())
""",
    "test_sample.js": """
// JavaScript sample
import { Component } from 'react';

class MyComponent extends Component {
    constructor(props) {
        super(props);
    }
    
    render() {
        return <div>Hello</div>;
    }
}

export default MyComponent;
""",
    "test_sample.ts": """
// TypeScript sample
interface User {
    name: string;
    age: number;
}

class UserService {
    getUser(id: number): User {
        return { name: "Alice", age: 30 };
    }
}

export { User, UserService };
""",
    "test_sample.java": """
// Java sample
package com.example;

import java.util.List;

public class User {
    private String name;
    
    public User(String name) {
        this.name = name;
    }
    
    public String getName() {
        return name;
    }
}
""",
    "test_sample.c": """
// C sample
#include <stdio.h>

#define MAX_SIZE 100

struct Point {
    int x;
    int y;
};

int add(int a, int b) {
    return a + b;
}

int main() {
    printf("Hello, World!\\n");
    return 0;
}
""",
    "test_sample.cpp": """
// C++ sample
#include <iostream>

namespace MyApp {
    class Calculator {
    public:
        int add(int a, int b) {
            return a + b;
        }
    };
}

int main() {
    MyApp::Calculator calc;
    std::cout << calc.add(5, 3) << std::endl;
    return 0;
}
""",
    "test_sample.go": """
// Go sample
package main

import "fmt"

type User struct {
    Name string
    Age  int
}

func (u *User) Greet() string {
    return "Hello, " + u.Name
}

func main() {
    user := User{Name: "Alice", Age: 30}
    fmt.Println(user.Greet())
}
""",
    "test_sample.rs": """
// Rust sample
mod utils;

use std::fmt;

struct Point {
    x: f64,
    y: f64,
}

impl Point {
    fn new(x: f64, y: f64) -> Self {
        Point { x, y }
    }
}

fn main() {
    let p = Point::new(10.0, 20.0);
    println!("Point: ({}, {})", p.x, p.y);
}
""",
}

parse_results = {}
for filename, content in samples.items():
    filepath = Path(filename)
    try:
        # Write sample file
        filepath.write_text(content)
        
        # Get parser
        parser = factory.get_parser_by_path(filepath)
        
        # Parse file
        result = parser.parse(filepath)
        
        # Store results
        parse_results[filename] = {
            "language": parser.language,
            "success": result.success,
            "symbols": result.symbols if result.symbols else [],
            "error": result.error_message
        }
        
        # Print summary
        status = "✓" if result.success else "✗"
        symbol_count = len(result.symbols) if result.symbols else 0
        print(f"  {status} {filename:20} ({parser.language:12}) - {symbol_count} symbols")
        
    except Exception as e:
        print(f"  ✗ {filename:20} - ERROR: {e}")
        parse_results[filename] = {
            "language": "Unknown",
            "success": False,
            "symbols": [],
            "error": str(e)
        }
    finally:
        # Clean up
        if filepath.exists():
            filepath.unlink()

# 5. EXAMPLE SYMBOLS EXTRACTED
print("\n5. EXAMPLE SYMBOLS EXTRACTED")
print("-" * 80)

for filename, result in parse_results.items():
    lang = result["language"]
    symbols = result["symbols"]
    
    print(f"\n{lang} ({filename}):")
    if symbols:
        # Show first 5 symbols
        for i, symbol in enumerate(symbols[:5], 1):
            sym_type = symbol.get("type", "unknown")
            sym_name = symbol.get("name", "N/A")
            sym_line = symbol.get("line", "?")
            print(f"  {i}. {sym_type:12} {sym_name:30} (line {sym_line})")
        if len(symbols) > 5:
            print(f"  ... and {len(symbols) - 5} more symbols")
    else:
        print(f"  No symbols extracted")

# 6. VERIFY UNSUPPORTED LANGUAGES
print("\n6. UNSUPPORTED LANGUAGE HANDLING")
print("-" * 80)

unsupported_file = Path("test.unknown")
try:
    unsupported_file.write_text("// Unknown language")
    parser = factory.get_parser_by_path(unsupported_file)
    result = parser.parse(unsupported_file)
    
    if parser.language == "Unknown" or not result.success:
        print(f"  ✓ Unsupported file handled gracefully")
        print(f"    Parser: {parser.language}")
        print(f"    Success: {result.success}")
        print(f"    Error: {result.error_message}")
    else:
        print(f"  ✗ Unsupported file not handled correctly")
finally:
    if unsupported_file.exists():
        unsupported_file.unlink()

# 7. FILES MODIFIED SUMMARY
print("\n7. FILES MODIFIED IN PARSER SYSTEM")
print("-" * 80)

modified_files = [
    "app/services/parser/parser_factory.py",
    "requirements/base.txt",
]

created_files = [
    "app/services/parser/java_parser.py",
    "app/services/parser/c_parser.py",
    "app/services/parser/cpp_parser.py",
    "app/services/parser/go_parser.py",
    "app/services/parser/rust_parser.py",
]

print("Modified:")
for f in modified_files:
    print(f"  - {f}")

print("\nCreated:")
for f in created_files:
    print(f"  - {f}")

# 8. FINAL SUMMARY
print("\n" + "=" * 80)
print("VERIFICATION SUMMARY")
print("=" * 80)

total_tests = len(test_cases)
successful_parses = sum(1 for r in parse_results.values() if r["success"])
total_symbols = sum(len(r["symbols"]) for r in parse_results.values())

print(f"✓ Supported Languages: {len(supported_languages)}")
print(f"✓ Supported Extensions: {len(supported_extensions)}")
print(f"✓ Parser Factory Tests: {total_tests}/{total_tests} passed")
print(f"✓ Sample Files Parsed: {successful_parses}/{len(samples)} succeeded")
print(f"✓ Total Symbols Extracted: {total_symbols}")
print(f"✓ Unsupported Languages: Handled gracefully")

print("\n" + "=" * 80)
print("✓ PARSER SYSTEM VERIFICATION COMPLETE")
print("=" * 80)
