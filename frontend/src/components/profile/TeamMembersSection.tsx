'use client';

/**
 * Team members section — company owner only.
 *
 * Owners (including standalone single-member companies, where the list is
 * just themselves) can add employee accounts and remove them with Delete.
 * Delete deactivates the account server-side (login dies instantly, data
 * rows stay company data) and the member drops off the team list.
 *
 * Pattern: SavedItemsSection.tsx — hand-rolled fixed inset-0 modal,
 * react-toastify feedback, window.confirm for removal.
 */

import { useState, useEffect } from 'react';
import { Button } from '@/components/ui/button';
import { Input } from '@/components/ui/input';
import { Label } from '@/components/ui/label';
import { Card, CardContent, CardHeader, CardTitle, CardDescription } from '@/components/ui/card';
import { toast } from 'react-toastify';
import { Users, Plus, Loader2, Copy, Shield, Trash2, X } from 'lucide-react';
import { companyApi, CompanyMember } from '@/services/companyApi';

export default function TeamMembersSection() {
  const [members, setMembers] = useState<CompanyMember[]>([]);
  const [loading, setLoading] = useState(true);
  const [showAddForm, setShowAddForm] = useState(false);
  const [saving, setSaving] = useState(false);
  const [deletingId, setDeletingId] = useState<string | null>(null);

  // Add-employee form state
  const [email, setEmail] = useState('');
  const [name, setName] = useState('');
  const [password, setPassword] = useState('');

  // Generated temporary password — returned once from the create response
  const [tempPassword, setTempPassword] = useState<string | null>(null);

  const loadMembers = async () => {
    try {
      setLoading(true);
      const data = await companyApi.listEmployees();
      setMembers(data.members || []);
    } catch (error) {
      toast.error(error instanceof Error ? error.message : 'Failed to load team members');
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    loadMembers();
  }, []);

  const resetForm = () => {
    setEmail('');
    setName('');
    setPassword('');
    setShowAddForm(false);
  };

  const handleAddEmployee = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!email.trim() || !name.trim()) {
      toast.error('Please fill in both email and name');
      return;
    }

    try {
      setSaving(true);
      const data = await companyApi.createEmployee({
        email: email.trim(),
        name: name.trim(),
        password: password.trim() ? password.trim() : undefined,
      });

      resetForm();
      toast.success(`Employee ${data.email} added!`);

      // Show the one-time temporary password (only when the server generated it)
      if (data.temporary_password) {
        setTempPassword(data.temporary_password);
      }

      await loadMembers();
    } catch (error) {
      toast.error(error instanceof Error ? error.message : 'Failed to add employee');
    } finally {
      setSaving(false);
    }
  };

  const handleCopyTempPassword = async () => {
    if (!tempPassword) return;
    try {
      await navigator.clipboard.writeText(tempPassword);
      toast.success('Password copied to clipboard');
    } catch {
      toast.error('Could not copy password — please copy it manually');
    }
  };

  const handleDeleteMember = async (member: CompanyMember) => {
    const confirmed = window.confirm(
      `Delete ${member.name} (${member.email}) from your team?\n\n` +
      'They will lose access immediately and be removed from this list. ' +
      'Their invoices and other data stay with the company for records and FBR audit.'
    );
    if (!confirmed) return;

    try {
      setDeletingId(member.id);
      // Delete = deactivation under the hood: access dies instantly, the
      // member drops off the team list (list API returns active members
      // only), but every row they created stays company data — never a
      // hard row deletion (FR-011).
      await companyApi.deactivateEmployee(member.id);
      toast.success(`${member.name} has been removed from the team`);
      await loadMembers();
    } catch (error) {
      toast.error(error instanceof Error ? error.message : 'Failed to delete employee');
    } finally {
      setDeletingId(null);
    }
  };

  return (
    <>
      <Card>
        <CardHeader>
          <CardTitle className="flex items-center gap-2 text-lg sm:text-xl">
            <Users className="h-5 w-5" />
            Team Members
          </CardTitle>
          <CardDescription className="text-sm">
            Add employee accounts for your staff. Employees share the company&apos;s data,
            invoices and saved products, but do not get Automation access.
          </CardDescription>
        </CardHeader>
        <CardContent>
          {loading ? (
            <div className="flex items-center justify-center py-8">
              <Loader2 className="h-6 w-6 animate-spin text-[#008060] dark:text-[#00a876]" />
            </div>
          ) : (
            <div className="space-y-3">
              {members.length === 0 && (
                <p className="text-sm text-[#6d7175] dark:text-[#8c9196] py-4 text-center">
                  No team members yet. Add your first employee to get started.
                </p>
              )}

              {members.map((member) => (
                <div
                  key={member.id}
                  className="flex flex-col sm:flex-row sm:items-center justify-between gap-3 p-3 rounded-xl border border-[#e1e3e5] dark:border-[#2e2e2e] bg-white dark:bg-[#161616]"
                >
                  <div className="flex items-center gap-3 min-w-0">
                    <div className="flex-shrink-0 h-9 w-9 rounded-full bg-[#008060]/10 dark:bg-[#00a876]/10 flex items-center justify-center">
                      <Users className="h-4 w-4 text-[#008060] dark:text-[#00a876]" />
                    </div>
                    <div className="min-w-0">
                      <p className="text-sm font-semibold text-[#202223] dark:text-[#e3e3e3] truncate flex items-center gap-2">
                        {member.name}
                        {member.is_company_owner && (
                          <span className="inline-flex items-center gap-1 px-2 py-0.5 rounded-full text-[10px] font-bold bg-[#dbeafe] text-[#1e40af] dark:bg-[#1e3a8a]/40 dark:text-[#60a5fa]">
                            <Shield className="h-3 w-3" />
                            Owner
                          </span>
                        )}
                        {member.automation_enabled && (
                          <span className="px-2 py-0.5 rounded-full text-[10px] font-bold bg-[#fef3c7] text-[#92400e] dark:bg-[#78350f]/40 dark:text-[#fbbf24]">
                            Automation
                          </span>
                        )}
                      </p>
                      <p className="text-xs text-[#6d7175] dark:text-[#8c9196] truncate">{member.email}</p>
                    </div>
                  </div>

                  {!member.is_company_owner && (
                    <Button
                      variant="outline"
                      size="sm"
                      disabled={deletingId === member.id}
                      onClick={() => handleDeleteMember(member)}
                      className="flex items-center gap-2 h-8 text-xs border-red-200 dark:border-red-900 text-red-600 dark:text-red-400 hover:bg-red-50 dark:hover:bg-red-950/30 shrink-0"
                    >
                      {deletingId === member.id ? (
                        <Loader2 className="h-3.5 w-3.5 animate-spin" />
                      ) : (
                        <Trash2 className="h-3.5 w-3.5" />
                      )}
                      Delete
                    </Button>
                  )}
                </div>
              ))}

              <Button
                size="default"
                onClick={() => setShowAddForm(true)}
                className="w-full h-10 text-sm bg-[#008060] hover:bg-[#006e52] text-white mt-2"
              >
                <Plus className="h-4 w-4 mr-2" />
                Add Employee
              </Button>
            </div>
          )}
        </CardContent>
      </Card>

      {/* One-time temporary password display */}
      {tempPassword && (
        <div className="fixed inset-0 z-[60] flex items-center justify-center p-4">
          <div
            className="absolute inset-0 bg-black/40 backdrop-blur-sm"
            onClick={() => setTempPassword(null)}
          />
          <div className="relative w-[95vw] max-w-md bg-white dark:bg-[#161616] rounded-2xl shadow-2xl border-2 border-[#008060] dark:border-[#00a876] p-6">
            <div className="flex items-center justify-between mb-2">
              <h4 className="text-base sm:text-lg font-bold text-[#202223] dark:text-[#e3e3e3]">
                Employee Created
              </h4>
              <button
                onClick={() => setTempPassword(null)}
                className="text-[#6d7175] dark:text-[#8c9196] hover:text-[#202223] dark:hover:text-[#e3e3e3]"
                aria-label="Close"
              >
                <X className="h-5 w-5" />
              </button>
            </div>
            <p className="text-sm text-[#6d7175] dark:text-[#8c9196] mb-4">
              Share this temporary password with the employee. It is shown{' '}
              <strong className="text-[#b45309] dark:text-[#fbbf24]">only once</strong> — after
              closing this window it cannot be retrieved.
            </p>
            <div className="flex items-center gap-2 p-3 rounded-xl bg-[#fef3c7] dark:bg-[#78350f]/30 border border-[#fcd34d] dark:border-[#b45309]/50 mb-3">
              <code className="flex-1 text-sm font-mono font-bold text-[#78350f] dark:text-[#fde68a] break-all">
                {tempPassword}
              </code>
              <Button
                type="button"
                size="sm"
                variant="outline"
                onClick={handleCopyTempPassword}
                className="flex items-center gap-1.5 h-8 text-xs shrink-0"
              >
                <Copy className="h-3.5 w-3.5" />
                Copy
              </Button>
            </div>
            <p className="text-xs text-[#6d7175] dark:text-[#8c9196]">
              The employee can log in immediately and should change their password after first login.
            </p>
            <Button
              className="w-full mt-4 h-10 bg-[#008060] hover:bg-[#006e52] text-white"
              onClick={() => setTempPassword(null)}
            >
              Done
            </Button>
          </div>
        </div>
      )}

      {/* Add employee modal */}
      {showAddForm && (
        <>
          <div
            className="fixed inset-0 z-[60] bg-black/40 backdrop-blur-sm transition-opacity"
            onClick={resetForm}
          />
          <div className="fixed inset-0 z-[60] flex items-start justify-center pt-2 sm:pt-10 overflow-y-auto">
            <div
              className="relative w-[95vw] max-w-lg bg-white dark:bg-[#161616] rounded-2xl shadow-2xl border-2 border-black dark:border-[#2e2e2e] mb-10"
              onClick={(e) => e.stopPropagation()}
            >
              <div className="flex items-center justify-between px-4 sm:px-6 py-3 border-b border-[#e1e3e5] dark:border-[#2e2e2e] bg-blue-100 dark:bg-blue-950/40 rounded-t-xl">
                <h4 className="text-base sm:text-lg font-bold text-[#202223] dark:text-[#e3e3e3]">
                  Add Employee
                </h4>
                <button
                  onClick={resetForm}
                  className="text-[#6d7175] dark:text-[#8c9196] hover:text-[#202223] dark:hover:text-[#e3e3e3]"
                  aria-label="Close"
                >
                  <X className="h-5 w-5" />
                </button>
              </div>

              <form onSubmit={handleAddEmployee} className="p-4 sm:p-6 space-y-4">
                <div className="space-y-2">
                  <Label htmlFor="employee-email" className="text-sm font-medium">
                    Email Address
                  </Label>
                  <Input
                    id="employee-email"
                    type="email"
                    required
                    placeholder="staff@company.pk"
                    value={email}
                    onChange={(e) => setEmail(e.target.value)}
                    className="border-[#e1e3e5] dark:border-[#2e2e2e] focus:border-[#008060] dark:focus:border-[#00a876] rounded-lg"
                  />
                </div>

                <div className="space-y-2">
                  <Label htmlFor="employee-name" className="text-sm font-medium">
                    Full Name
                  </Label>
                  <Input
                    id="employee-name"
                    required
                    placeholder="Staff Member"
                    value={name}
                    onChange={(e) => setName(e.target.value)}
                    className="border-[#e1e3e5] dark:border-[#2e2e2e] focus:border-[#008060] dark:focus:border-[#00a876] rounded-lg"
                  />
                </div>

                <div className="space-y-2">
                  <Label htmlFor="employee-password" className="text-sm font-medium">
                    Temporary Password <span className="text-[#6d7175] dark:text-[#8c9196] font-normal">(optional)</span>
                  </Label>
                  <Input
                    id="employee-password"
                    type="text"
                    placeholder="Leave empty to auto-generate a strong password"
                    value={password}
                    onChange={(e) => setPassword(e.target.value)}
                    className="border-[#e1e3e5] dark:border-[#2e2e2e] focus:border-[#008060] dark:focus:border-[#00a876] rounded-lg"
                  />
                  <p className="text-xs text-[#6d7175] dark:text-[#8c9196]">
                    If left empty, a secure temporary password is generated and shown once.
                  </p>
                </div>

                <div className="flex items-center justify-end gap-3 pt-2">
                  <Button
                    type="button"
                    variant="outline"
                    onClick={resetForm}
                    className="h-10 px-4 text-sm border-[#e1e3e5] dark:border-[#2e2e2e]"
                  >
                    Cancel
                  </Button>
                  <Button
                    type="submit"
                    disabled={saving}
                    className="h-10 px-4 text-sm bg-[#008060] hover:bg-[#006e52] text-white"
                  >
                    {saving ? (
                      <>
                        <Loader2 className="h-4 w-4 animate-spin mr-2" />
                        Creating...
                      </>
                    ) : (
                      <>
                        <Plus className="h-4 w-4 mr-2" />
                        Create Employee
                      </>
                    )}
                  </Button>
                </div>
              </form>
            </div>
          </div>
        </>
      )}
    </>
  );
}
