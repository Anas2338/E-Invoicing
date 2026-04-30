'use client';

import { useState, useEffect } from 'react';
import { adminApi, PendingUser } from '@/services/adminApi';
import { CheckCircle, XCircle, Trash2, RefreshCw } from 'lucide-react';

export default function AdminUsersPage() {
  const [pendingUsers, setPendingUsers] = useState<PendingUser[]>([]);
  const [allUsers, setAllUsers] = useState<PendingUser[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [actionLoading, setActionLoading] = useState<string | null>(null);
  const [activeTab, setActiveTab] = useState<'pending' | 'all'>('pending');
  const [rejectionReason, setRejectionReason] = useState<{ [key: string]: string }>({});
  const [showRejectModal, setShowRejectModal] = useState<string | null>(null);
  const [togglingAutomation, setTogglingAutomation] = useState<string | null>(null);

  useEffect(() => {
    loadUsers();
  }, [activeTab]);

  const loadUsers = async () => {
    try {
      setLoading(true);
      setError(null);

      if (activeTab === 'pending') {
        const response = await adminApi.getPendingUsers();
        setPendingUsers(response.users);
      } else {
        const response = await adminApi.getAllUsers();
        console.log('All Users Response:', response);
        console.log('First user automation_enabled:', response.users[0]?.automation_enabled);
        setAllUsers(response.users);
      }
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Failed to load users');
    } finally {
      setLoading(false);
    }
  };

  const handleApprove = async (userId: string) => {
    try {
      setActionLoading(userId);
      await adminApi.approveUser(userId);
      await loadUsers();
      alert('User approved successfully!');
    } catch (err) {
      alert(err instanceof Error ? err.message : 'Failed to approve user');
    } finally {
      setActionLoading(null);
    }
  };

  const handleReject = async (userId: string) => {
    try {
      setActionLoading(userId);
      const reason = rejectionReason[userId] || 'No reason provided';
      await adminApi.rejectUser(userId, reason);
      await loadUsers();
      setShowRejectModal(null);
      setRejectionReason({ ...rejectionReason, [userId]: '' });
      alert('User rejected successfully!');
    } catch (err) {
      alert(err instanceof Error ? err.message : 'Failed to reject user');
    } finally {
      setActionLoading(null);
    }
  };

  const handleDelete = async (userId: string) => {
    if (!confirm('Are you sure you want to delete this user? This action cannot be undone.')) {
      return;
    }

    try {
      setActionLoading(userId);
      await adminApi.deleteUser(userId);
      await loadUsers();
      alert('User deleted successfully!');
    } catch (err) {
      alert(err instanceof Error ? err.message : 'Failed to delete user');
    } finally {
      setActionLoading(null);
    }
  };

  const handleToggleAutomation = async (userId: string, currentStatus: boolean) => {
    const action = currentStatus ? 'disable' : 'enable';
    if (!confirm(`Are you sure you want to ${action} automation access for this user?`)) {
      return;
    }

    try {
      setTogglingAutomation(userId);
      await adminApi.toggleAutomationAccess(userId, !currentStatus);
      await loadUsers();
      alert(`Automation access ${action}d successfully!`);
    } catch (err) {
      alert(err instanceof Error ? err.message : `Failed to ${action} automation access`);
    } finally {
      setTogglingAutomation(null);
    }
  };

  const getStatusBadge = (status: string) => {
    switch (status) {
      case 'pending':
        return 'bg-yellow-100 text-yellow-800 dark:bg-yellow-900/30 dark:text-yellow-400';
      case 'approved':
        return 'bg-green-100 text-green-800 dark:bg-green-900/30 dark:text-green-400';
      case 'rejected':
        return 'bg-red-100 text-red-800 dark:bg-red-900/30 dark:text-red-400';
      default:
        return 'bg-gray-100 text-gray-800 dark:bg-gray-900/30 dark:text-gray-400';
    }
  };

  const users = activeTab === 'pending' ? pendingUsers : allUsers;

  return (
    <div className="container mx-auto px-3 sm:px-4 lg:px-6 py-4 sm:py-6 lg:py-8">
      <div className="mb-6 sm:mb-8">
        <h1 className="text-2xl sm:text-3xl font-bold text-[#202223] dark:text-[#e3e3e3] mb-2">
          User Management
        </h1>
        <p className="text-sm sm:text-base text-[#6d7175] dark:text-[#8c9196]">
          Approve or reject user registrations
        </p>
      </div>

      {/* Tabs */}
      <div className="mb-4 sm:mb-6 border-b border-[#e1e3e5] dark:border-[#2e2e2e] overflow-x-auto">
        <div className="flex gap-2 sm:gap-4 min-w-max">
          <button
            onClick={() => setActiveTab('pending')}
            className={`pb-3 px-1 text-sm sm:text-base font-semibold transition-colors whitespace-nowrap ${
              activeTab === 'pending'
                ? 'text-[#008060] dark:text-[#00a876] border-b-2 border-[#008060] dark:border-[#00a876]'
                : 'text-[#6d7175] dark:text-[#8c9196] hover:text-[#202223] dark:hover:text-[#e3e3e3]'
            }`}
          >
            Pending ({pendingUsers.length})
          </button>
          <button
            onClick={() => setActiveTab('all')}
            className={`pb-3 px-1 text-sm sm:text-base font-semibold transition-colors whitespace-nowrap ${
              activeTab === 'all'
                ? 'text-[#008060] dark:text-[#00a876] border-b-2 border-[#008060] dark:border-[#00a876]'
                : 'text-[#6d7175] dark:text-[#8c9196] hover:text-[#202223] dark:hover:text-[#e3e3e3]'
            }`}
          >
            All Users ({allUsers.length})
          </button>
        </div>
      </div>

      {/* Refresh Button */}
      <div className="mb-4 flex justify-end">
        <button
          onClick={loadUsers}
          disabled={loading}
          className="flex items-center gap-2 px-3 sm:px-4 py-2 text-sm sm:text-base bg-[#008060] dark:bg-[#00a876] text-white rounded-lg hover:bg-[#006e52] dark:hover:bg-[#008f64] disabled:opacity-50 transition-colors"
        >
          <RefreshCw className={`w-4 h-4 ${loading ? 'animate-spin' : ''}`} />
          <span className="hidden sm:inline">Refresh</span>
        </button>
      </div>

      {/* Error Message */}
      {error && (
        <div className="mb-4 bg-red-50 dark:bg-red-900/20 border border-red-200 dark:border-red-800 rounded-lg p-3 sm:p-4">
          <p className="text-sm sm:text-base text-red-800 dark:text-red-400">{error}</p>
        </div>
      )}

      {/* Loading/Empty States */}
      {loading ? (
        <div className="flex items-center justify-center py-12">
          <div className="text-sm sm:text-base text-[#6d7175] dark:text-[#8c9196]">Loading users...</div>
        </div>
      ) : users.length === 0 ? (
        <div className="bg-white dark:bg-[#1a1a1a] rounded-xl border border-[#e1e3e5] dark:border-[#2e2e2e] p-8 sm:p-12 text-center">
          <p className="text-sm sm:text-base text-[#6d7175] dark:text-[#8c9196]">
            {activeTab === 'pending' ? 'No pending users' : 'No users found'}
          </p>
        </div>
      ) : (
        <>
          {/* Mobile/Tablet Card View */}
          <div className="md:hidden space-y-4">
            {users.map((user) => (
              <div
                key={user.id}
                className="bg-white dark:bg-[#1a1a1a] rounded-xl border border-[#e1e3e5] dark:border-[#2e2e2e] p-4 space-y-3"
              >
                {/* User Info */}
                <div className="space-y-2">
                  <div>
                    <div className="text-xs text-[#6d7175] dark:text-[#8c9196] mb-1">Name</div>
                    <div className="text-sm font-semibold text-[#202223] dark:text-[#e3e3e3]">
                      {user.name || 'N/A'}
                    </div>
                  </div>
                  <div>
                    <div className="text-xs text-[#6d7175] dark:text-[#8c9196] mb-1">Email</div>
                    <div className="text-sm text-[#202223] dark:text-[#e3e3e3] break-all">
                      {user.email}
                    </div>
                  </div>
                  <div>
                    <div className="text-xs text-[#6d7175] dark:text-[#8c9196] mb-1">Registered</div>
                    <div className="text-sm text-[#202223] dark:text-[#e3e3e3]">
                      {new Date(user.created_at).toLocaleDateString()}
                    </div>
                  </div>
                  {activeTab === 'all' && (
                    <>
                      <div>
                        <div className="text-xs text-[#6d7175] dark:text-[#8c9196] mb-1">Status</div>
                        <span className={`inline-block px-2 py-1 text-xs font-semibold rounded-lg ${getStatusBadge(user.account_status)}`}>
                          {user.account_status}
                        </span>
                      </div>
                      <div>
                        <div className="text-xs text-[#6d7175] dark:text-[#8c9196] mb-2">Automation</div>
                        <button
                          onClick={() => {
                            console.log('Toggle clicked for user:', user.id, 'Current status:', user.automation_enabled);
                            handleToggleAutomation(user.id, user.automation_enabled);
                          }}
                          disabled={togglingAutomation === user.id || user.account_status !== 'approved'}
                          className={`w-full px-4 py-2 text-xs font-semibold rounded-lg transition-all duration-200 border-2 ${
                            user.automation_enabled
                              ? 'bg-green-500 text-white border-green-600 hover:bg-green-600'
                              : 'bg-gray-500 text-white border-gray-600 hover:bg-gray-600'
                          } disabled:opacity-50 disabled:cursor-not-allowed`}
                        >
                          {togglingAutomation === user.id ? 'Updating...' : (user.automation_enabled ? '✓ Enabled' : '✗ Disabled')}
                        </button>
                      </div>
                    </>
                  )}
                </div>

                {/* Actions */}
                <div className="pt-3 border-t border-[#e1e3e5] dark:border-[#2e2e2e] space-y-2">
                  {user.account_status === 'pending' && (
                    <div className="flex gap-2">
                      <button
                        onClick={() => handleApprove(user.id)}
                        disabled={actionLoading === user.id}
                        className="flex-1 flex items-center justify-center gap-1 px-3 py-2 text-sm bg-green-600 text-white rounded-lg hover:bg-green-700 disabled:opacity-50 transition-colors"
                      >
                        <CheckCircle className="w-4 h-4" />
                        Approve
                      </button>
                      <button
                        onClick={() => setShowRejectModal(user.id)}
                        disabled={actionLoading === user.id}
                        className="flex-1 flex items-center justify-center gap-1 px-3 py-2 text-sm bg-red-600 text-white rounded-lg hover:bg-red-700 disabled:opacity-50 transition-colors"
                      >
                        <XCircle className="w-4 h-4" />
                        Reject
                      </button>
                    </div>
                  )}
                  {activeTab === 'all' && (
                    <button
                      onClick={() => handleDelete(user.id)}
                      disabled={actionLoading === user.id}
                      className="w-full flex items-center justify-center gap-1 px-3 py-2 text-sm bg-gray-600 text-white rounded-lg hover:bg-gray-700 disabled:opacity-50 transition-colors"
                    >
                      <Trash2 className="w-4 h-4" />
                      Delete
                    </button>
                  )}
                </div>
              </div>
            ))}
          </div>

          {/* Desktop Table View */}
          <div className="hidden md:block bg-white dark:bg-[#1a1a1a] rounded-xl border border-[#e1e3e5] dark:border-[#2e2e2e] overflow-x-auto">
            <table className="w-full">
              <thead className="bg-[#f6f6f7] dark:bg-[#2e2e2e]">
                <tr>
                  <th className="px-4 lg:px-6 py-3 text-left text-xs font-semibold text-[#6d7175] dark:text-[#8c9196] uppercase tracking-wider">
                    Name
                  </th>
                  <th className="px-4 lg:px-6 py-3 text-left text-xs font-semibold text-[#6d7175] dark:text-[#8c9196] uppercase tracking-wider">
                    Email
                  </th>
                  <th className="px-4 lg:px-6 py-3 text-left text-xs font-semibold text-[#6d7175] dark:text-[#8c9196] uppercase tracking-wider">
                    Registered
                  </th>
                  {activeTab === 'all' && (
                    <>
                      <th className="px-4 lg:px-6 py-3 text-left text-xs font-semibold text-[#6d7175] dark:text-[#8c9196] uppercase tracking-wider">
                        Status
                      </th>
                      <th className="px-4 lg:px-6 py-3 text-left text-xs font-semibold text-[#6d7175] dark:text-[#8c9196] uppercase tracking-wider">
                        Automation
                      </th>
                    </>
                  )}
                  <th className="px-4 lg:px-6 py-3 text-right text-xs font-semibold text-[#6d7175] dark:text-[#8c9196] uppercase tracking-wider">
                    Actions
                  </th>
                </tr>
              </thead>
              <tbody className="divide-y divide-[#e1e3e5] dark:divide-[#2e2e2e]">
                {users.map((user) => (
                  <tr key={user.id} className="hover:bg-[#f6f6f7] dark:hover:bg-[#2e2e2e] transition-colors">
                    <td className="px-4 lg:px-6 py-4 whitespace-nowrap">
                      <div className="text-sm font-semibold text-[#202223] dark:text-[#e3e3e3]">
                        {user.name || 'N/A'}
                      </div>
                    </td>
                    <td className="px-4 lg:px-6 py-4">
                      <div className="text-sm text-[#6d7175] dark:text-[#8c9196] max-w-xs truncate">
                        {user.email}
                      </div>
                    </td>
                    <td className="px-4 lg:px-6 py-4 whitespace-nowrap">
                      <div className="text-sm text-[#6d7175] dark:text-[#8c9196]">
                        {new Date(user.created_at).toLocaleDateString()}
                      </div>
                    </td>
                    {activeTab === 'all' && (
                      <>
                        <td className="px-4 lg:px-6 py-4 whitespace-nowrap">
                          <span className={`px-2 py-1 text-xs font-semibold rounded-lg ${getStatusBadge(user.account_status)}`}>
                            {user.account_status}
                          </span>
                        </td>
                        <td className="px-4 lg:px-6 py-4 whitespace-nowrap">
                          <button
                            onClick={() => {
                              console.log('Toggle clicked for user:', user.id, 'Current status:', user.automation_enabled);
                              handleToggleAutomation(user.id, user.automation_enabled);
                            }}
                            disabled={togglingAutomation === user.id || user.account_status !== 'approved'}
                            className={`px-3 lg:px-4 py-2 text-xs font-semibold rounded-lg transition-all duration-200 border-2 cursor-pointer ${
                              user.automation_enabled
                                ? 'bg-green-500 text-white border-green-600 hover:bg-green-600 hover:shadow-md'
                                : 'bg-gray-500 text-white border-gray-600 hover:bg-gray-600 hover:shadow-md'
                            } disabled:opacity-50 disabled:cursor-not-allowed disabled:hover:shadow-none`}
                          >
                            {togglingAutomation === user.id ? 'Updating...' : (user.automation_enabled ? '✓ Enabled' : '✗ Disabled')}
                          </button>
                        </td>
                      </>
                    )}
                    <td className="px-4 lg:px-6 py-4 whitespace-nowrap text-right text-sm font-medium">
                      <div className="flex items-center justify-end gap-2">
                        {user.account_status === 'pending' && (
                          <>
                            <button
                              onClick={() => handleApprove(user.id)}
                              disabled={actionLoading === user.id}
                              className="flex items-center gap-1 px-2 lg:px-3 py-1 text-xs lg:text-sm bg-green-600 text-white rounded-lg hover:bg-green-700 disabled:opacity-50 transition-colors"
                            >
                              <CheckCircle className="w-4 h-4" />
                              <span className="hidden lg:inline">Approve</span>
                            </button>
                            <button
                              onClick={() => setShowRejectModal(user.id)}
                              disabled={actionLoading === user.id}
                              className="flex items-center gap-1 px-2 lg:px-3 py-1 text-xs lg:text-sm bg-red-600 text-white rounded-lg hover:bg-red-700 disabled:opacity-50 transition-colors"
                            >
                              <XCircle className="w-4 h-4" />
                              <span className="hidden lg:inline">Reject</span>
                            </button>
                          </>
                        )}
                        {activeTab === 'all' && (
                          <button
                            onClick={() => handleDelete(user.id)}
                            disabled={actionLoading === user.id}
                            className="flex items-center gap-1 px-2 lg:px-3 py-1 text-xs lg:text-sm bg-gray-600 text-white rounded-lg hover:bg-gray-700 disabled:opacity-50 transition-colors"
                          >
                            <Trash2 className="w-4 h-4" />
                            <span className="hidden lg:inline">Delete</span>
                          </button>
                        )}
                      </div>
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        </>
      )}

      {/* Reject Modal */}
      {showRejectModal && (
        <div className="fixed inset-0 bg-black/50 flex items-center justify-center z-50 p-4">
          <div className="bg-white dark:bg-[#1a1a1a] rounded-xl p-4 sm:p-6 max-w-md w-full border border-[#e1e3e5] dark:border-[#2e2e2e]">
            <h3 className="text-base sm:text-lg font-bold text-[#202223] dark:text-[#e3e3e3] mb-3 sm:mb-4">
              Reject User Registration
            </h3>
            <p className="text-xs sm:text-sm text-[#6d7175] dark:text-[#8c9196] mb-3 sm:mb-4">
              Please provide a reason for rejecting this user's registration:
            </p>
            <textarea
              value={rejectionReason[showRejectModal] || ''}
              onChange={(e) => setRejectionReason({ ...rejectionReason, [showRejectModal]: e.target.value })}
              className="w-full px-3 py-2 text-sm sm:text-base border border-[#c9cccf] dark:border-[#2e2e2e] rounded-lg bg-white dark:bg-[#1a1a1a] text-[#202223] dark:text-[#e3e3e3] focus:outline-none focus:ring-2 focus:ring-[#008060] dark:focus:ring-[#00a876]"
              rows={4}
              placeholder="Enter rejection reason..."
            />
            <div className="flex flex-col sm:flex-row gap-2 mt-4">
              <button
                onClick={() => handleReject(showRejectModal)}
                disabled={actionLoading === showRejectModal}
                className="flex-1 px-4 py-2 text-sm sm:text-base bg-red-600 text-white rounded-lg hover:bg-red-700 disabled:opacity-50 transition-colors"
              >
                Confirm Reject
              </button>
              <button
                onClick={() => setShowRejectModal(null)}
                disabled={actionLoading === showRejectModal}
                className="flex-1 px-4 py-2 text-sm sm:text-base bg-gray-200 dark:bg-gray-700 text-gray-700 dark:text-gray-300 rounded-lg hover:bg-gray-300 dark:hover:bg-gray-600 transition-colors"
              >
                Cancel
              </button>
            </div>
          </div>
        </div>
      )}
    </div>
  );
}
