(globalThis.TURBOPACK || (globalThis.TURBOPACK = [])).push([typeof document === "object" ? document.currentScript : undefined,
"[project]/src/providers/auth-provider.tsx [app-client] (ecmascript)", ((__turbopack_context__) => {
"use strict";

__turbopack_context__.s([
    "AuthProvider",
    ()=>AuthProvider,
    "useAuth",
    ()=>useAuth
]);
var __TURBOPACK__imported__module__$5b$project$5d2f$node_modules$2f$next$2f$dist$2f$build$2f$polyfills$2f$process$2e$js__$5b$app$2d$client$5d$__$28$ecmascript$29$__ = /*#__PURE__*/ __turbopack_context__.i("[project]/node_modules/next/dist/build/polyfills/process.js [app-client] (ecmascript)");
var __TURBOPACK__imported__module__$5b$project$5d2f$node_modules$2f$next$2f$dist$2f$compiled$2f$react$2f$jsx$2d$dev$2d$runtime$2e$js__$5b$app$2d$client$5d$__$28$ecmascript$29$__ = __turbopack_context__.i("[project]/node_modules/next/dist/compiled/react/jsx-dev-runtime.js [app-client] (ecmascript)");
var __TURBOPACK__imported__module__$5b$project$5d2f$node_modules$2f$next$2f$dist$2f$compiled$2f$react$2f$index$2e$js__$5b$app$2d$client$5d$__$28$ecmascript$29$__ = __turbopack_context__.i("[project]/node_modules/next/dist/compiled/react/index.js [app-client] (ecmascript)");
var __TURBOPACK__imported__module__$5b$project$5d2f$node_modules$2f$next$2f$navigation$2e$js__$5b$app$2d$client$5d$__$28$ecmascript$29$__ = __turbopack_context__.i("[project]/node_modules/next/navigation.js [app-client] (ecmascript)");
;
var _s = __turbopack_context__.k.signature(), _s1 = __turbopack_context__.k.signature();
'use client';
;
;
// API Base URL
const API_BASE_URL = ("TURBOPACK compile-time value", "http://localhost:8001/api/v1") || 'http://localhost:8001/api/v1';
// Create context
const AuthContext = /*#__PURE__*/ (0, __TURBOPACK__imported__module__$5b$project$5d2f$node_modules$2f$next$2f$dist$2f$compiled$2f$react$2f$index$2e$js__$5b$app$2d$client$5d$__$28$ecmascript$29$__["createContext"])(undefined);
function AuthProvider({ children }) {
    _s();
    const [user, setUser] = (0, __TURBOPACK__imported__module__$5b$project$5d2f$node_modules$2f$next$2f$dist$2f$compiled$2f$react$2f$index$2e$js__$5b$app$2d$client$5d$__$28$ecmascript$29$__["useState"])(null);
    const [loading, setLoading] = (0, __TURBOPACK__imported__module__$5b$project$5d2f$node_modules$2f$next$2f$dist$2f$compiled$2f$react$2f$index$2e$js__$5b$app$2d$client$5d$__$28$ecmascript$29$__["useState"])(true);
    const router = (0, __TURBOPACK__imported__module__$5b$project$5d2f$node_modules$2f$next$2f$navigation$2e$js__$5b$app$2d$client$5d$__$28$ecmascript$29$__["useRouter"])();
    // Check if user is authenticated on mount
    (0, __TURBOPACK__imported__module__$5b$project$5d2f$node_modules$2f$next$2f$dist$2f$compiled$2f$react$2f$index$2e$js__$5b$app$2d$client$5d$__$28$ecmascript$29$__["useEffect"])({
        "AuthProvider.useEffect": ()=>{
            const checkAuthStatus = {
                "AuthProvider.useEffect.checkAuthStatus": async ()=>{
                    try {
                        const storedUser = localStorage.getItem('user');
                        const storedToken = localStorage.getItem('access_token');
                        // Both user and token must exist
                        if (storedUser && storedToken) {
                            setUser(JSON.parse(storedUser));
                        } else {
                            // Clear any partial auth data
                            localStorage.removeItem('user');
                            localStorage.removeItem('access_token');
                            setUser(null);
                        }
                    } catch (error) {
                        console.error('Error checking auth status:', error);
                        // Clear invalid data
                        localStorage.removeItem('user');
                        localStorage.removeItem('access_token');
                        setUser(null);
                    } finally{
                        setLoading(false);
                    }
                }
            }["AuthProvider.useEffect.checkAuthStatus"];
            checkAuthStatus();
        }
    }["AuthProvider.useEffect"], []);
    const signIn = async (email, password)=>{
        setLoading(true);
        try {
            const response = await fetch(`${API_BASE_URL}/auth/login`, {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json'
                },
                body: JSON.stringify({
                    email,
                    password
                })
            });
            if (!response.ok) {
                const errorData = await response.json().catch(()=>({
                        error: 'Login failed'
                    }));
                console.error('Login error:', errorData);
                setLoading(false);
                throw new Error(errorData.detail || errorData.error || 'Invalid credentials');
            }
            const data = await response.json();
            if (data.access_token) {
                localStorage.setItem('access_token', data.access_token);
            }
            if (data.user) {
                localStorage.setItem('user', JSON.stringify(data.user));
            }
            const tokenCheck = localStorage.getItem('access_token');
            const userCheck = localStorage.getItem('user');
            if (!tokenCheck || !userCheck) {
                console.error('Failed to verify stored data');
                setLoading(false);
                throw new Error('Failed to store authentication data');
            }
            setUser(data.user);
            await new Promise((resolve)=>setTimeout(resolve, 100));
            window.location.href = '/dashboard';
        } catch (error) {
            console.error('Sign in error:', error);
            setLoading(false);
            throw error;
        }
    };
    const signUp = async (email, password, name)=>{
        setLoading(true);
        try {
            // Simulate API call to sign up
            const response = await fetch(`${API_BASE_URL}/auth/register`, {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json'
                },
                body: JSON.stringify({
                    email,
                    password,
                    name
                })
            });
            if (response.ok) {
                const data = await response.json();
                setUser(data.user);
                localStorage.setItem('user', JSON.stringify(data.user));
                router.push('/dashboard');
            } else {
                const errorData = await response.json();
                throw new Error(errorData.error || 'Registration failed');
            }
        } catch (error) {
            console.error('Sign up error:', error);
            throw error;
        } finally{
            setLoading(false);
        }
    };
    const signOut = async ()=>{
        try {
        // Optional: call backend logout endpoint if it exists
        // await fetch(`${API_BASE_URL}/auth/logout`, { method: 'POST' });
        } catch (error) {
            console.error('Sign out error:', error);
        } finally{
            setUser(null);
            localStorage.removeItem('user');
            localStorage.removeItem('access_token');
            router.push('/login');
        }
    };
    const value = {
        user,
        loading,
        signIn,
        signUp,
        signOut,
        isAuthenticated: !!user
    };
    return /*#__PURE__*/ (0, __TURBOPACK__imported__module__$5b$project$5d2f$node_modules$2f$next$2f$dist$2f$compiled$2f$react$2f$jsx$2d$dev$2d$runtime$2e$js__$5b$app$2d$client$5d$__$28$ecmascript$29$__["jsxDEV"])(AuthContext.Provider, {
        value: value,
        children: children
    }, void 0, false, {
        fileName: "[project]/src/providers/auth-provider.tsx",
        lineNumber: 171,
        columnNumber: 10
    }, this);
}
_s(AuthProvider, "J17Kp8z+0ojgAqGoY5o3BCjwWms=", false, function() {
    return [
        __TURBOPACK__imported__module__$5b$project$5d2f$node_modules$2f$next$2f$navigation$2e$js__$5b$app$2d$client$5d$__$28$ecmascript$29$__["useRouter"]
    ];
});
_c = AuthProvider;
function useAuth() {
    _s1();
    const context = (0, __TURBOPACK__imported__module__$5b$project$5d2f$node_modules$2f$next$2f$dist$2f$compiled$2f$react$2f$index$2e$js__$5b$app$2d$client$5d$__$28$ecmascript$29$__["useContext"])(AuthContext);
    if (context === undefined) {
        throw new Error('useAuth must be used within an AuthProvider');
    }
    return context;
}
_s1(useAuth, "b9L3QQ+jgeyIrH0NfHrJ8nn7VMU=");
var _c;
__turbopack_context__.k.register(_c, "AuthProvider");
if (typeof globalThis.$RefreshHelpers$ === 'object' && globalThis.$RefreshHelpers !== null) {
    __turbopack_context__.k.registerExports(__turbopack_context__.m, globalThis.$RefreshHelpers$);
}
}),
]);

//# sourceMappingURL=src_providers_auth-provider_tsx_d5231fea._.js.map