// Minimal TypeScript file
interface User {
    id: number;
    name: string;
}

type Point = { x: number; y: number };

enum Color {
    Red = "RED",
    Green = "GREEN"
}

function add(a: number, b: number): number {
    return a + b;
}

class Calculator {
    multiply(x: number, y: number): number {
        return x * y;
    }
}

export const PI = 3.14;