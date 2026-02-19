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
"[project]/src/app/api/auth/login/route.ts [app-route] (ecmascript)", ((__turbopack_context__) => {
"use strict";

__turbopack_context__.s([
    "POST",
    ()=>POST
]);
var __TURBOPACK__imported__module__$5b$project$5d2f$src$2f$lib$2f$db$2e$ts__$5b$app$2d$route$5d$__$28$ecmascript$29$__ = __turbopack_context__.i("[project]/src/lib/db.ts [app-route] (ecmascript)");
;
async function POST(request) {
    try {
        const { email, password } = await request.json();
        // Basic validation
        if (!email || !password) {
            return Response.json({
                error: 'Email and password are required'
            }, {
                status: 400
            });
        }
        // Find user
        const user = __TURBOPACK__imported__module__$5b$project$5d2f$src$2f$lib$2f$db$2e$ts__$5b$app$2d$route$5d$__$28$ecmascript$29$__["db"].getUserByEmail(email);
        if (!user) {
            return Response.json({
                error: 'Invalid credentials'
            }, {
                status: 401
            });
        }
        // In a real app, you'd compare hashed passwords
        // For this demo, we'll allow login with any password for non-admin users
        // But for the default admin user, we'll check for a specific password
        if (user.email === 'admin@example.com') {
            // For the admin user, check for a specific password
            if (password !== 'password123') {
                return Response.json({
                    error: 'Invalid credentials'
                }, {
                    status: 401
                });
            }
        }
        // Return user data (excluding password)
        const { password: _, ...userWithoutPassword } = user;
        return Response.json({
            user: userWithoutPassword,
            message: 'Login successful'
        });
    } catch (error) {
        console.error('Login error:', error);
        return Response.json({
            error: 'Login failed'
        }, {
            status: 500
        });
    }
}
}),
];

//# sourceMappingURL=%5Broot-of-the-server%5D__d82f5a16._.js.map