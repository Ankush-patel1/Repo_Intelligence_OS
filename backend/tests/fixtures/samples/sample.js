/**
 * Sample JavaScript file for testing parser.
 */

import { useState } from 'react';
import axios from 'axios';

export const API_URL = 'https://api.example.com';

function regularFunction(x, y) {
    return x + y;
}

async function asyncFunction(url) {
    const response = await fetch(url);
    return response.json();
}

const arrowFunction = (name) => {
    return `Hello, ${name}`;
};

const asyncArrowFunction = async (id) => {
    return await fetchData(id);
};

class SampleClass {
    constructor(name) {
        this.name = name;
    }

    instanceMethod() {
        return this.name.toUpperCase();
    }

    async asyncMethod() {
        return await this.fetchData();
    }

    static staticMethod() {
        return 'static';
    }
}

export function exportedFunction() {
    return 'exported';
}

export default SampleClass;
