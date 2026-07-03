"""Manual verification of the complete parser system."""

from pathlib import Path

# Import parsers directly to avoid circular import
from app.services.parser.c_parser import CTreeSitterParser
from app.services.parser.cpp_parser import CppTreeSitterParser
from app.services.parser.go_parser import GoTreeSitterParser
from app.services.parser.java_parser import JavaTreeSitterParser
from app.services.parser.javascript_parser import JavaScriptTreeSitterParser
from app.services.parser.python_parser import PythonTreeSitterParser
from app.services.parser.rust_parser import RustTreeSitterParser
from app.services.parser.typescript_parser import TypeScriptTreeSitterParser

print("=" * 80)
print("PARSER SYSTEM VERIFICATION - DIRECT PARSER TESTING")
print("=" * 80)

# Define test samples
samples = {
    "Python": {
        "file": "test_sample.py",
        "parser": PythonTreeSitterParser(),
        "content": '''# Python sample
import os

class MyClass:
    def __init__(self, name):
        self.name = name
    
    def greet(self):
        return f"Hello, {self.name}"

def main():
    obj = MyClass("World")
    print(obj.greet())
''',
    },
    "JavaScript": {
        "file": "test_sample.js",
        "parser": JavaScriptTreeSitterParser(),
        "content": '''// JavaScript sample
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
''',
    },
    "TypeScript": {
        "file": "test_sample.ts",
        "parser": TypeScriptTreeSitterParser(),
        "content": '''// TypeScript sample
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
''',
    },
    "Java": {
        "file": "test_sample.java",
        "parser": JavaTreeSitterParser(),
        "content": '''// Java sample
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
''',
    },
    "C": {
        "file": "test_sample.c",
        "parser": CTreeSitterParser(),
        "content": '''// C sample
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
''',
    },
    "C++": {
        "file": "test_sample.cpp",
        "parser": CppTreeSitterParser(),
        "content": '''// C++ sample
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
''',
    },
    "Go": {
        "file": "test_sample.go",
        "parser": GoTreeSitterParser(),
        "content": '''// Go sample
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
''',
    },
    "Rust": {
        "file": "test_sample.rs",
        "parser": RustTreeSitterParser(),
        "content": '''// Rust sample
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
''',
    },
}

print("\n1. SUPPORTED LANGUAGES")
print("-" * 80)
languages = list(samples.keys())
print(f"Total: {len(languages)} languages")
for i, lang in enumerate(languages, 1):
    parser = samples[lang]["parser"]
    exts = ", ".join(parser.supported_extensions)
    print(f"  {i}. {lang:12} - Extensions: {exts}")

print("\n2. PARSING VERIFICATION")
print("-" * 80)

parse_results = {}
for lang, data in samples.items():
    filepath = Path(data["file"])
    parser = data["parser"]
    content = data["content"]
    
    try:
        # Write sample file
        filepath.write_text(content)
        
        # Parse file
        result = parser.parse(filepath)
        
        # Store results
        parse_results[lang] = {
            "success": result.success,
            "symbols": result.symbols if result.symbols else [],
            "error": result.error_message
        }
        
        # Print summary
        status = "✓" if result.success else "✗"
        symbol_count = len(result.symbols) if result.symbols else 0
        print(f"  {status} {lang:12} - {symbol_count} symbols extracted")
        
    except Exception as e:
        print(f"  ✗ {lang:12} - ERROR: {e}")
        parse_results[lang] = {
            "success": False,
            "symbols": [],
            "error": str(e)
        }
    finally:
        # Clean up
        if filepath.exists():
            filepath.unlink()

print("\n3. EXAMPLE SYMBOLS EXTRACTED")
print("-" * 80)

for lang, result in parse_results.items():
    symbols = result["symbols"]
    
    print(f"\n{lang}:")
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

print("\n4. VERIFICATION SUMMARY")
print("=" * 80)

successful_parses = sum(1 for r in parse_results.values() if r["success"])
total_symbols = sum(len(r["symbols"]) for r in parse_results.values())

print(f"✓ Supported Languages: {len(languages)}")
print(f"✓ Sample Files Parsed: {successful_parses}/{len(samples)}")
print(f"✓ Total Symbols Extracted: {total_symbols}")

if successful_parses == len(samples):
    print("\n✓ ALL PARSERS WORKING CORRECTLY")
else:
    print(f"\n⚠ {len(samples) - successful_parses} parser(s) failed")

print("=" * 80)
