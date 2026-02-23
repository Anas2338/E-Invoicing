# Tasks: FBR Invoice Integration Portal - Frontend

**Input**: Design documents from `/specs/002-fbr-invoice-portal/`
**Prerequisites**: plan.md (required), spec.md (required for user stories)
**Status**: ✅ COMPLETED - All tasks implemented

**Tests**: Not included in current implementation

**Organization**: Tasks are grouped by user story to enable independent implementation and testing of each story.

## Format: `[ID] [P?] [Story] Description`

- **[P]**: Can run in parallel (different files, no dependencies)
- **[Story]**: Which user story this task belongs to (e.g., US1, US2, US3)
- **[x]**: Task completed
- Include exact file paths in descriptions

## Path Conventions

- **Web app**: `frontend/src/` for all frontend code
- All paths relative to repository root

---

## Phase 1: Setup (Shared Infrastructure)

**Purpose**: Project initialization and basic structure

- [x] T001 Initialize Next.js 16.1.6 project with TypeScript 5.9.3 in frontend/
- [x] T002 Install core dependencies (React 19.2.4, Tailwind CSS 4.1.18, TypeScript)
- [x] T003 [P] Configure Tailwind CSS 4.1 in frontend/tailwind.config.js
- [x] T004 [P] Configure TypeScript strict mode in frontend/tsconfig.json
- [x] T005 [P] Set up Next.js App Router configuration in frontend/next.config.js
- [x] T006 [P] Create environment variables template in frontend/.env.local
- [x] T007 Create project folder structure (app, components, lib, providers)
- [x] T008 [P] Install UI dependencies (Lucide React, Radix UI, React Hook Form, Zod)
- [x] T009 [P] Install notification library (React Toastify)
- [x] T010 [P] Configure global styles in frontend/src/app/globals.css

---

## Phase 2: Foundational (Blocking Prerequisites)

**Purpose**: Core infrastructure that MUST be complete before ANY user story can be implemented

**⚠️ CRITICAL**: No user story work can begin until this phase is complete

- [x] T011 Create API client base class in frontend/src/lib/api/api-client.ts
- [x] T012 [P] Create utility functions in frontend/src/lib/utils.ts
- [x] T013 [P] Create base UI components (button, input, label, card) in frontend/src/components/ui/
- [x] T014 [P] Create select component in frontend/src/components/ui/select.tsx
- [x] T015 [P] Create checkbox component in frontend/src/components/ui/checkbox.tsx
- [x] T016 [P] Create badge component in frontend/src/components/ui/badge.tsx
- [x] T017 [P] Create dropdown-menu component in frontend/src/components/ui/dropdown-menu.tsx
- [x] T018 Create root layout with providers in frontend/src/app/layout.tsx
- [x] T019 Create home page in frontend/src/app/page.tsx
- [x] T020 [P] Create global loading component in frontend/src/app/loading.tsx
- [x] T021 [P] Create global 404 page in frontend/src/app/not-found.tsx
- [x] T022 [P] Create error boundary component in frontend/src/components/common/error-boundary.tsx
- [x] T023 [P] Create loading skeleton component in frontend/src/components/common/loading-skeleton.tsx
- [x] T024 [P] Create toast notification component in frontend/src/components/common/toast.tsx

**Checkpoint**: Foundation ready - user story implementation can now begin in parallel

---

## Phase 3: User Story 2 - User Authentication and Session Management (Priority: P1) 🎯 MVP Foundation

**Goal**: Enable users to sign up, log in, maintain sessions, and log out securely

**Independent Test**: Complete signup flow, log in, refresh browser to verify session persistence, log out and verify redirect to login

### Implementation for User Story 2

- [x] T025 [P] [US2] Create AuthProvider context in frontend/src/providers/auth-provider.tsx
- [x] T026 [P] [US2] Create auth layout in frontend/src/app/(auth)/layout.tsx
- [x] T027 [P] [US2] Create login page in frontend/src/app/(auth)/login/page.tsx
- [x] T028 [P] [US2] Create register page in frontend/src/app/(auth)/register/page.tsx
- [x] T029 [P] [US2] Create LoginForm component in frontend/src/components/auth/login-form.tsx
- [x] T030 [P] [US2] Create RegisterForm component in frontend/src/components/auth/register-form.tsx
- [x] T031 [P] [US2] Create LogoutButton component in frontend/src/components/auth/logout-button.tsx
- [x] T032 [US2] Create AuthService class in frontend/src/lib/api/api-client.ts
- [x] T033 [P] [US2] Create login API route in frontend/src/app/api/auth/login/route.ts
- [x] T034 [P] [US2] Create register API route in frontend/src/app/api/auth/register/route.ts
- [x] T035 [P] [US2] Create logout API route in frontend/src/app/api/auth/logout/route.ts
- [x] T036 [P] [US2] Create forgot password page in frontend/src/app/auth/forgot-password/page.tsx
- [x] T037 [P] [US2] Create reset password page in frontend/src/app/auth/reset-password/page.tsx
- [x] T038 [US2] Create protected layout with route checks in frontend/src/app/(protected)/layout.tsx
- [x] T039 [US2] Implement session persistence with localStorage
- [x] T040 [US2] Implement automatic redirect on 401 responses
- [x] T041 [US2] Add form validation and error handling

**Checkpoint**: At this point, User Story 2 should be fully functional - users can sign up, log in, maintain sessions, and log out

---

## Phase 4: User Story 1 - Complete Invoice Submission Flow (Priority: P1) 🎯 MVP Core

**Goal**: Enable users to create, validate, and post sale invoices to FBR

**Independent Test**: Log in, create a sale invoice with all required fields, validate it, navigate to validated invoices, post it to FBR sandbox, verify it appears in history with "Posted" status

### Implementation for User Story 1

- [x] T042 [P] [US1] Create dashboard page in frontend/src/app/(protected)/dashboard/page.tsx
- [x] T043 [P] [US1] Create SummaryCard component in frontend/src/components/dashboard/summary-card.tsx
- [x] T044 [P] [US1] Create RecentInvoices component in frontend/src/components/dashboard/recent-invoices.tsx
- [x] T045 [P] [US1] Create UserProfileCard component in frontend/src/components/dashboard/user-profile-card.tsx
- [x] T046 [P] [US1] Create QuickActionsPanel component in frontend/src/components/dashboard/quick-actions-panel.tsx
- [x] T047 [P] [US1] Create Navigation component in frontend/src/components/navigation.tsx
- [x] T048 [US1] Create InvoiceService class in frontend/src/lib/api/api-client.ts
- [x] T049 [US1] Create MasterDataService class in frontend/src/lib/api/api-client.ts
- [x] T050 [US1] Create FBRIntegrationService class in frontend/src/lib/api/api-client.ts
- [x] T051 [US1] Create simplified API wrapper in frontend/src/lib/api.ts
- [x] T052 [US1] Create invoice validation schema in frontend/src/lib/validation/invoice-schema.ts
- [x] T053 [US1] Create invoice creation page in frontend/src/app/(protected)/invoices/create/page.tsx
- [x] T054 [US1] Create SaleInvoiceForm component (1089 lines) in frontend/src/components/invoices/sale-invoice-form.tsx
- [x] T055 [US1] Implement dynamic line items array with add/remove functionality
- [x] T056 [US1] Implement auto-calculation logic for totals (total value → sales tax and value excluding tax)
- [x] T057 [US1] Implement master data integration (provinces, UOM, tax rates, HS codes, etc.)
- [x] T058 [US1] Implement buyer verification with FBR API
- [x] T059 [US1] Implement HS code autocomplete with suggestions
- [x] T060 [US1] Implement dynamic UOM filtering based on selected HS code
- [x] T061 [US1] Implement SRO schedule lookup based on tax rate and invoice date
- [x] T062 [US1] Add client-side validation for all required fields
- [x] T063 [US1] Create validated invoices page in frontend/src/app/(protected)/invoices/validated/page.tsx
- [x] T064 [US1] Create InvoiceTable component in frontend/src/components/invoices/invoice-table.tsx
- [x] T065 [US1] Create ValidationResultDialog component in frontend/src/components/invoices/validation-result-dialog.tsx
- [x] T066 [US1] Implement invoice validation flow (call backend validation endpoint)
- [x] T067 [US1] Implement invoice posting flow (call backend posting endpoint)
- [x] T068 [US1] Add validation error display with user-friendly messages
- [x] T069 [US1] Add posting success/failure feedback
- [x] T070 [US1] Create invoice details page in frontend/src/app/(protected)/invoices/[id]/page.tsx
- [x] T071 [US1] Display full invoice data including FBR response

**Checkpoint**: At this point, User Story 1 should be fully functional - users can create, validate, and post sale invoices to FBR

---

## Phase 5: User Story 5 - Invoice History and Search (Priority: P3)

**Goal**: Enable users to view all invoices with filtering and search capabilities

**Independent Test**: Create invoices with different dates, types, and statuses, then apply various filter combinations and verify results

### Implementation for User Story 5

- [x] T072 [P] [US5] Create invoice history page in frontend/src/app/(protected)/invoices/history/page.tsx
- [x] T073 [US5] Implement invoice table with filtering by status, type, environment
- [x] T074 [US5] Implement date range filtering
- [x] T075 [US5] Implement search functionality
- [x] T076 [US5] Implement pagination
- [x] T077 [US5] Add "View Details" action for each invoice
- [x] T078 [US5] Display FBR response data in invoice details

**Checkpoint**: At this point, User Story 5 should be fully functional - users can view and filter invoice history

---

## Phase 6: User Story 7 - Draft Invoice Management (Priority: P3)

**Goal**: Enable users to save, edit, and manage draft invoices

**Independent Test**: Create a draft invoice, save it, log out, log back in, edit the draft, complete and validate it

### Implementation for User Story 7

- [x] T079 [P] [US7] Create invoice edit page in frontend/src/app/(protected)/invoices/[id]/edit/page.tsx
- [x] T080 [US7] Implement form pre-population with existing invoice data
- [x] T081 [US7] Implement update functionality for draft invoices
- [x] T082 [US7] Add delete draft functionality
- [x] T083 [US7] Display draft invoices on dashboard with edit option
- [x] T084 [US7] Add "Save Draft" functionality to invoice form

**Checkpoint**: At this point, User Story 7 should be fully functional - users can save, edit, and manage draft invoices

---

## Phase 7: User Story 6 - Purchase Invoice Creation (Priority: P3)

**Goal**: Enable users to create purchase invoices in addition to sale invoices

**Independent Test**: Create a purchase invoice with all required fields, validate it, and post it to FBR

### Implementation for User Story 6

- [x] T085 [P] [US6] Create PurchaseInvoiceForm component in frontend/src/components/invoices/purchase-invoice-form.tsx
- [x] T086 [US6] Implement purchase-specific fields and validation
- [x] T087 [US6] Add invoice type selector to creation page
- [x] T088 [US6] Implement purchase invoice validation flow
- [x] T089 [US6] Implement purchase invoice posting flow

**Checkpoint**: At this point, User Story 6 should be fully functional - users can create, validate, and post purchase invoices

---

## Phase 8: User Story 3 - Environment Selection and Production Readiness (Priority: P2)

**Goal**: Enable users to switch between Sandbox and Production environments

**Independent Test**: Toggle environment selector, verify sandbox is default, confirm production mode requires approval flag

### Implementation for User Story 3

- [x] T090 [P] [US3] Create EnvironmentSelector component in frontend/src/components/common/environment-selector.tsx
- [x] T091 [US3] Create UserService class in frontend/src/lib/api/api-client.ts
- [x] T092 [US3] Implement environment state management
- [x] T093 [US3] Add environment parameter to all invoice API calls
- [x] T094 [US3] Implement production approval check
- [x] T095 [US3] Add visual indicator for current environment
- [x] T096 [US3] Add warnings for production mode operations

**Checkpoint**: At this point, User Story 3 should be fully functional - users can switch between environments

---

## Phase 9: User Story 4 - Bulk Invoice Posting (Priority: P2)

**Goal**: Enable users to select and post multiple validated invoices at once

**Independent Test**: Create and validate 5+ invoices, select multiple via checkboxes, click "Post Selected", verify all are posted

### Implementation for User Story 4

- [x] T097 [US4] Add checkbox selection to invoice table
- [x] T098 [US4] Add "Post Selected" button to validated invoices page
- [x] T099 [US4] Implement bulk posting API call
- [x] T100 [US4] Add posting progress indicator
- [x] T101 [US4] Display individual success/failure results for each invoice
- [x] T102 [US4] Update table after bulk posting completes

**Checkpoint**: At this point, User Story 4 should be fully functional - users can bulk post multiple invoices

---

## Phase 10: Additional Features & Polish

**Purpose**: Additional pages and improvements

- [x] T103 [P] Create profile page in frontend/src/app/(protected)/profile/page.tsx
- [x] T104 [P] Add FBR credentials management to profile page
- [x] T105 [P] Create settings page in frontend/src/app/(protected)/settings/page.tsx
- [x] T106 [P] Create help page in frontend/src/app/(protected)/help/page.tsx
- [x] T107 [P] Add loading states to all pages
- [x] T108 [P] Add error handling to all API calls
- [x] T109 [P] Implement automatic token cleanup on 401 responses
- [x] T110 [P] Add responsive design for mobile and tablet
- [x] T111 [P] Optimize form performance for 100+ line items
- [x] T112 [P] Add debounced buyer verification (1 second delay)
- [x] T113 [P] Implement useCallback for form update handlers

---

## Dependencies & Execution Order

### Phase Dependencies

- **Setup (Phase 1)**: ✅ COMPLETED - No dependencies
- **Foundational (Phase 2)**: ✅ COMPLETED - Depends on Setup completion
- **User Story 2 (Phase 3)**: ✅ COMPLETED - Depends on Foundational phase (authentication is prerequisite)
- **User Story 1 (Phase 4)**: ✅ COMPLETED - Depends on US2 (requires authentication)
- **User Story 5 (Phase 5)**: ✅ COMPLETED - Depends on US1 (requires invoices to exist)
- **User Story 7 (Phase 6)**: ✅ COMPLETED - Depends on US1 (extends invoice creation)
- **User Story 6 (Phase 7)**: ✅ COMPLETED - Depends on US1 (similar to sale invoices)
- **User Story 3 (Phase 8)**: ✅ COMPLETED - Depends on US1 (extends invoice workflow)
- **User Story 4 (Phase 9)**: ✅ COMPLETED - Depends on US1 (extends posting workflow)
- **Polish (Phase 10)**: ✅ COMPLETED - Depends on all user stories

### User Story Dependencies

- **User Story 2 (P1)**: ✅ COMPLETED - Authentication foundation, no dependencies on other stories
- **User Story 1 (P1)**: ✅ COMPLETED - Depends on US2 (requires authentication)
- **User Story 5 (P3)**: ✅ COMPLETED - Depends on US1 (requires invoices to exist)
- **User Story 7 (P3)**: ✅ COMPLETED - Depends on US1 (extends invoice creation)
- **User Story 6 (P3)**: ✅ COMPLETED - Depends on US1 (similar workflow)
- **User Story 3 (P2)**: ✅ COMPLETED - Depends on US1 (extends invoice workflow)
- **User Story 4 (P2)**: ✅ COMPLETED - Depends on US1 (extends posting workflow)

### Within Each User Story

- Authentication before all protected features
- API services before components that use them
- Base components before feature components
- Forms before validation and submission
- Core implementation before enhancements

### Parallel Opportunities

- All Setup tasks marked [P] can run in parallel
- All Foundational tasks marked [P] can run in parallel
- UI components within a story marked [P] can run in parallel
- Different user stories can be worked on in parallel by different team members (after dependencies met)

---

## Parallel Example: User Story 1

```bash
# Launch all dashboard components together:
Task T043: "Create SummaryCard component"
Task T044: "Create RecentInvoices component"
Task T045: "Create UserProfileCard component"
Task T046: "Create QuickActionsPanel component"

# Launch all service classes together:
Task T048: "Create InvoiceService class"
Task T049: "Create MasterDataService class"
Task T050: "Create FBRIntegrationService class"
```

---

## Implementation Strategy

### MVP First (User Stories 2 + 1)

1. ✅ Complete Phase 1: Setup
2. ✅ Complete Phase 2: Foundational
3. ✅ Complete Phase 3: User Story 2 (Authentication)
4. ✅ Complete Phase 4: User Story 1 (Invoice Submission)
5. ✅ VALIDATE: Test complete invoice lifecycle independently
6. ✅ Deploy/demo ready

### Incremental Delivery

1. ✅ Setup + Foundational → Foundation ready
2. ✅ Add User Story 2 → Authentication working
3. ✅ Add User Story 1 → Invoice submission working (MVP!)
4. ✅ Add User Story 5 → Invoice history working
5. ✅ Add User Story 7 → Draft management working
6. ✅ Add User Story 6 → Purchase invoices working
7. ✅ Add User Story 3 → Environment selection working
8. ✅ Add User Story 4 → Bulk posting working
9. ✅ Each story adds value without breaking previous stories

### Actual Implementation Order

The frontend was implemented in the following order:
1. ✅ Setup and foundational infrastructure
2. ✅ Authentication (US2) - Required for all other features
3. ✅ Dashboard and navigation
4. ✅ Invoice creation with master data integration (US1)
5. ✅ Validation and posting workflows (US1)
6. ✅ Invoice history and filtering (US5)
7. ✅ Draft management (US7)
8. ✅ Purchase invoices (US6)
9. ✅ Environment selection (US3)
10. ✅ Bulk posting (US4)
11. ✅ Profile, settings, and help pages
12. ✅ Polish and optimization

---

## Implementation Summary

### Total Tasks: 113 (All Completed ✅)

**By Phase**:
- Phase 1 (Setup): 10 tasks ✅
- Phase 2 (Foundational): 14 tasks ✅
- Phase 3 (US2 - Authentication): 17 tasks ✅
- Phase 4 (US1 - Invoice Submission): 30 tasks ✅
- Phase 5 (US5 - Invoice History): 7 tasks ✅
- Phase 6 (US7 - Draft Management): 6 tasks ✅
- Phase 7 (US6 - Purchase Invoices): 5 tasks ✅
- Phase 8 (US3 - Environment Selection): 7 tasks ✅
- Phase 9 (US4 - Bulk Posting): 6 tasks ✅
- Phase 10 (Polish): 11 tasks ✅

**By User Story**:
- US1 (Invoice Submission): 30 tasks ✅
- US2 (Authentication): 17 tasks ✅
- US3 (Environment Selection): 7 tasks ✅
- US4 (Bulk Posting): 6 tasks ✅
- US5 (Invoice History): 7 tasks ✅
- US6 (Purchase Invoices): 5 tasks ✅
- US7 (Draft Management): 6 tasks ✅

**Parallel Opportunities**: 45 tasks marked [P] could have been executed in parallel

**Independent Test Criteria**: Each user story has clear acceptance criteria and can be tested independently

**MVP Scope**: User Stories 2 + 1 (Authentication + Invoice Submission) = 47 tasks

---

## Key Implementation Highlights

### Architecture Decisions
- ✅ Custom authentication with localStorage (not Better Auth)
- ✅ Native React hooks for state management (not React Query)
- ✅ Service class API architecture with 5 service classes
- ✅ Custom UI components with Tailwind CSS 4.1 (not shadcn/ui)
- ✅ Comprehensive master data integration with FBR

### Major Components
- ✅ SaleInvoiceForm: 1089 lines with full FBR integration
- ✅ PurchaseInvoiceForm: Similar complexity for purchase invoices
- ✅ InvoiceTable: Filtering, sorting, and bulk operations
- ✅ Dashboard: Stats cards, recent invoices, quick actions
- ✅ Navigation: Sidebar with all protected routes

### API Integration
- ✅ 5 service classes: Auth, Invoice, User, MasterData, FBRIntegration
- ✅ 20+ API endpoints integrated
- ✅ Automatic token management and 401 handling
- ✅ Type-safe API calls with TypeScript

### Form Features
- ✅ Dynamic line items with add/remove
- ✅ Auto-calculation of totals and taxes
- ✅ Master data integration (provinces, UOM, tax rates, HS codes)
- ✅ Buyer verification with FBR
- ✅ HS code autocomplete with suggestions
- ✅ Dynamic UOM filtering based on HS code
- ✅ SRO schedule lookup based on tax rate and date
- ✅ Client-side validation before submission
- ✅ Edit mode with form pre-population

### Performance Optimizations
- ✅ useCallback for form update handlers
- ✅ Debounced buyer verification (1 second delay)
- ✅ Optimized line item rendering for 100+ items
- ✅ Master data cached on component mount

---

## Notes

- All tasks completed ✅
- [P] tasks = different files, no dependencies
- [Story] label maps task to specific user story for traceability
- Each user story is independently completable and testable
- Frontend follows all constitution requirements
- No tests implemented in current version
- All API calls go through backend (no direct FBR API calls)
- Type-safe implementation with TypeScript strict mode
