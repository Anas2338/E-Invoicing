module.exports = [
"[externals]/next/dist/compiled/next-server/app-route-turbo.runtime.dev.js [external] (next/dist/compiled/next-server/app-route-turbo.runtime.dev.js, cjs)", ((__turbopack_context__, module, exports) => {

const mod = __turbopack_context__.x("next/dist/compiled/next-server/app-route-turbo.runtime.dev.js", () => require("next/dist/compiled/next-server/app-route-turbo.runtime.dev.js"));

module.exports = mod;
}),
"[externals]/next/dist/compiled/@opentelemetry/api [external] (next/dist/compiled/@opentelemetry/api, cjs)", ((__turbopack_context__, module, exports) => {

const mod = __turbopack_context__.x("next/dist/compiled/@opentelemetry/api", () => require("next/dist/compiled/@opentelemetry/api"));

module.exports = mod;
}),
"[externals]/next/dist/compiled/next-server/app-page-turbo.runtime.dev.js [external] (next/dist/compiled/next-server/app-page-turbo.runtime.dev.js, cjs)", ((__turbopack_context__, module, exports) => {

const mod = __turbopack_context__.x("next/dist/compiled/next-server/app-page-turbo.runtime.dev.js", () => require("next/dist/compiled/next-server/app-page-turbo.runtime.dev.js"));

module.exports = mod;
}),
"[externals]/next/dist/server/app-render/work-unit-async-storage.external.js [external] (next/dist/server/app-render/work-unit-async-storage.external.js, cjs)", ((__turbopack_context__, module, exports) => {

const mod = __turbopack_context__.x("next/dist/server/app-render/work-unit-async-storage.external.js", () => require("next/dist/server/app-render/work-unit-async-storage.external.js"));

module.exports = mod;
}),
"[externals]/next/dist/server/app-render/work-async-storage.external.js [external] (next/dist/server/app-render/work-async-storage.external.js, cjs)", ((__turbopack_context__, module, exports) => {

const mod = __turbopack_context__.x("next/dist/server/app-render/work-async-storage.external.js", () => require("next/dist/server/app-render/work-async-storage.external.js"));

module.exports = mod;
}),
"[externals]/next/dist/shared/lib/no-fallback-error.external.js [external] (next/dist/shared/lib/no-fallback-error.external.js, cjs)", ((__turbopack_context__, module, exports) => {

const mod = __turbopack_context__.x("next/dist/shared/lib/no-fallback-error.external.js", () => require("next/dist/shared/lib/no-fallback-error.external.js"));

module.exports = mod;
}),
"[project]/src/lib/db.ts [app-route] (ecmascript)", ((__turbopack_context__) => {
"use strict";

// Simple in-memory storage for demo purposes
// In a real app, you'd use a proper database
__turbopack_context__.s([
    "db",
    ()=>db
]);
class InMemoryDB {
    users = [
        {
            id: '1',
            email: 'admin@example.com',
            name: 'Admin User',
            password: '$2a$10$8K1p/a0SIuTGZBhpZuzxZOYq8YEGP18/YkYNWdOvM5ebEa1OD/WjW',
            productionAccessApproved: true
        }
    ];
    getUserByEmail(email) {
        return this.users.find((user)=>user.email === email);
    }
    getUserById(id) {
        return this.users.find((user)=>user.id === id);
    }
    addUser(user) {
        const newUser = {
            ...user,
            id: Date.now().toString()
        };
        this.users.push(newUser);
        return newUser;
    }
    getAllUsers() {
        return [
            ...this.users
        ]; // Return a copy
    }
}
const db = new InMemoryDB();
}),
"[project]/src/app/api/auth/register/route.ts [app-route] (ecmascript)", ((__turbopack_context__) => {
"use strict";

__turbopack_context__.s([
    "POST",
    ()=>POST
]);
var __TURBOPACK__imported__module__$5b$project$5d2f$src$2f$lib$2f$db$2e$ts__$5b$app$2d$route$5d$__$28$ecmascript$29$__ = __turbopack_context__.i("[project]/src/lib/db.ts [app-route] (ecmascript)");
;
async function POST(request) {
    try {
        const { email, password, name } = await request.json();
        // Basic validation
        if (!email || !password || !name) {
            return Response.json({
                error: 'Email, password, and name are required'
            }, {
                status: 400
            });
        }
        // Email validation
        const emailRegex = /^[^\s@]+@[^\s@]+\.[^\s@]+$/;
        if (!emailRegex.test(email)) {
            return Response.json({
                error: 'Invalid email format'
            }, {
                status: 400
            });
        }
        // Password validation
        if (password.length < 8) {
            return Response.json({
                error: 'Password must be at least 8 characters'
            }, {
                status: 400
            });
        }
        if (!/(?=.*[a-z])(?=.*[A-Z])(?=.*\d)(?=.*[@$!%*?&])[A-Za-z\d@$!%*?&]/.test(password)) {
            return Response.json({
                error: 'Password must contain uppercase, lowercase, number, and special character'
            }, {
                status: 400
            });
        }
        // Check if user already exists
        const existingUser = __TURBOPACK__imported__module__$5b$project$5d2f$src$2f$lib$2f$db$2e$ts__$5b$app$2d$route$5d$__$28$ecmascript$29$__["db"].getUserByEmail(email);
        if (existingUser) {
            return Response.json({
                error: 'User with this email already exists'
            }, {
                status: 409
            });
        }
        // For this demo, let's just return a success response
        // In a real app, you'd hash the password and save to database
        const newUser = __TURBOPACK__imported__module__$5b$project$5d2f$src$2f$lib$2f$db$2e$ts__$5b$app$2d$route$5d$__$28$ecmascript$29$__["db"].addUser({
            email,
            name,
            password,
            productionAccessApproved: false
        });
        // Remove password from response
        const { password: _, ...userWithoutPassword } = newUser;
        return Response.json({
            user: userWithoutPassword,
            message: 'User registered successfully'
        });
    } catch (error) {
        console.error('Registration error:', error);
        return Response.json({
            error: 'Registration failed'
        }, {
            status: 500
        });
    }
}
}),
];

//# sourceMappingURL=%5Broot-of-the-server%5D__23816012._.js.map