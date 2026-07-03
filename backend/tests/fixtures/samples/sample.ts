/**
 * Sample TypeScript file for testing parser.
 */

import { Component } from 'react';

export interface User {
    id: number;
    name: string;
    email: string;
}

export type UserId = number | string;

export enum Status {
    Active = 'active',
    Inactive = 'inactive',
    Pending = 'pending'
}

function typedFunction(x: number, y: number): number {
    return x + y;
}

async function asyncTypedFunction(url: string): Promise<Response> {
    return await fetch(url);
}

const arrowFunction = (name: string): string => {
    return `Hello, ${name}`;
};

class TypedClass implements User {
    constructor(
        public id: number,
        public name: string,
        public email: string
    ) {}

    instanceMethod(): string {
        return this.name.toUpperCase();
    }

    async asyncMethod(): Promise<void> {
        await this.fetchData();
    }

    static staticMethod(): string {
        return 'static';
    }
}

export { TypedClass };
export default typedFunction;
