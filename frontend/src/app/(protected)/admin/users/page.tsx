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
    <div className="container mx-auto px-4 py-8">
      <div className="mb-8">
        <h1 className="text-3xl font-bold text-[#202223] dark:text-[#e3e3e3] mb-2">
          User Management
        </h1>
        <p className="text-[#6d7175] dark:text-[#8c9196]">
          Approve or reject user registrations
        </p>
      </div>

      {/* Tabs */}
      <div className="mb-6 border-b border-[#e1e3e5] dark:border-[#2e2e2e]">
        <div className="flex gap-4">
          <button
            onClick={() => setActiveTab('pending')}
            className={`pb-3 px-1 font-semibold transition-colors ${
              activeTab === 'pending'
                ? 'text-[#008060] dark:text-[#00a876] border-b-2 border-[#008060] dark:border-[#00a876]'
                : 'text-[#6d7175] dark:text-[#8c9196] hover:text-[#202223] dark:hover:text-[#e3e3e3]'
            }`}
          >
            Pending Approvals ({pendingUsers.length})
          </button>
          <button
            onClick={() => setActiveTab('all')}
            className={`pb-3 px-1 font-semibold transition-colors ${
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
          className="flex items-center gap-2 px-4 py-2 bg-[#008060] dark:bg-[#00a876] text-white rounded-lg hover:bg-[#006e52] dark:hover:bg-[#008f64] disabled:opacity-50 transition-colors"
        >
          <RefreshCw className={`w-4 h-4 ${loading ? 'animate-spin' : ''}`} />
          Refresh
        </button>
      </div>

      {/* Error Message */}
      {error && (
        <div className="mb-4 bg-red-50 dark:bg-red-900/20 border border-red-200 dark:border-red-800 rounded-lg p-4">
          <p className="text-red-800 dark:text-red-400">{error}</p>
        </div>
      )}

      {/* Users Table */}
      {loading ? (
        <div className="flex items-center justify-center py-12">
          <div className="text-[#6d7175] dark:text-[#8c9196]">Loading users...</div>
        </div>
      ) : users.length === 0 ? (
        <div className="bg-white dark:bg-[#1a1a1a] rounded-xl border border-[#e1e3e5] dark:border-[#2e2e2e] p-12 text-center">
          <p className="text-[#6d7175] dark:text-[#8c9196]">
            {activeTab === 'pending' ? 'No pending users' : 'No users found'}
          </p>
        </div>
      ) : (
        <div className="bg-white dark:bg-[#1a1a1a] rounded-xl border border-[#e1e3e5] dark:border-[#2e2e2e] overflow-hidden">
          <table className="w-full">
            <thead className="bg-[#f6f6f7] dark:bg-[#2e2e2e]">
              <tr>
                <th className="px-6 py-3 text-left text-xs font-semibold text-[#6d7175] dark:text-[#8c9196] uppercase tracking-wider">
                  Name
                </th>
                <th className="px-6 py-3 text-left text-xs font-semibold text-[#6d7175] dark:text-[#8c9196] uppercase tracking-wider">
                  Email
                </th>
                <th className="px-6 py-3 text-left text-xs font-semibold text-[#6d7175] dark:text-[#8c9196] uppercase tracking-wider">
                  Registered
                </th>
                {activeTab === 'all' && (
                  <th className="px-6 py-3 text-left text-xs font-semibold text-[#6d7175] dark:text-[#8c9196] uppercase tracking-wider">
                    Status
                  </th>
                )}
                <th className="px-6 py-3 text-right text-xs font-semibold text-[#6d7175] dark:text-[#8c9196] uppercase tracking-wider">
                  Actions
                </th>
              </tr>
            </thead>
            <tbody className="divide-y divide-[#e1e3e5] dark:divide-[#2e2e2e]">
              {users.map((user) => (
                <tr key={user.id} className="hover:bg-[#f6f6f7] dark:hover:bg-[#2e2e2e] transition-colors">
                  <td className="px-6 py-4 whitespace-nowrap">
                    <div className="text-sm font-semibold text-[#202223] dark:text-[#e3e3e3]">
                      {user.name || 'N/A'}
                    </div>
                  </td>
                  <td className="px-6 py-4 whitespace-nowrap">
                    <div className="text-sm text-[#6d7175] dark:text-[#8c9196]">{user.email}</div>
                  </td>
                  <td className="px-6 py-4 whitespace-nowrap">
                    <div className="text-sm text-[#6d7175] dark:text-[#8c9196]">
                      {new Date(user.created_at).toLocaleDateString()}
                    </div>
                  </td>
                  {activeTab === 'all' && (
                    <td className="px-6 py-4 whitespace-nowrap">
                      <span className={`px-2 py-1 text-xs font-semibold rounded-lg ${getStatusBadge(user.account_status)}`}>
                        {user.account_status}
                      </span>
                    </td>
                  )}
                  <td className="px-6 py-4 whitespace-nowrap text-right text-sm font-medium">
                    <div className="flex items-center justify-end gap-2">
                      {user.account_status === 'pending' && (
                        <>
                          <button
                            onClick={() => handleApprove(user.id)}
                            disabled={actionLoading === user.id}
                            className="flex items-center gap-1 px-3 py-1 bg-green-600 text-white rounded-lg hover:bg-green-700 disabled:opacity-50 transition-colors"
                          >
                            <CheckCircle className="w-4 h-4" />
                            Approve
                          </button>
                          <button
                            onClick={() => setShowRejectModal(user.id)}
                            disabled={actionLoading === user.id}
                            className="flex items-center gap-1 px-3 py-1 bg-red-600 text-white rounded-lg hover:bg-red-700 disabled:opacity-50 transition-colors"
                          >
                            <XCircle className="w-4 h-4" />
                            Reject
                          </button>
                        </>
                      )}
                      {activeTab === 'all' && (
                        <button
                          onClick={() => handleDelete(user.id)}
                          disabled={actionLoading === user.id}
                          className="flex items-center gap-1 px-3 py-1 bg-gray-600 text-white rounded-lg hover:bg-gray-700 disabled:opacity-50 transition-colors"
                        >
                          <Trash2 className="w-4 h-4" />
                          Delete
                        </button>
                      )}
                    </div>
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      )}

      {/* Reject Modal */}
      {showRejectModal && (
        <div className="fixed inset-0 bg-black/50 flex items-center justify-center z-50">
          <div className="bg-white dark:bg-[#1a1a1a] rounded-xl p-6 max-w-md w-full mx-4 border border-[#e1e3e5] dark:border-[#2e2e2e]">
            <h3 className="text-lg font-bold text-[#202223] dark:text-[#e3e3e3] mb-4">
              Reject User Registration
            </h3>
            <p className="text-sm text-[#6d7175] dark:text-[#8c9196] mb-4">
              Please provide a reason for rejecting this user's registration:
            </p>
            <textarea
              value={rejectionReason[showRejectModal] || ''}
              onChange={(e) => setRejectionReason({ ...rejectionReason, [showRejectModal]: e.target.value })}
              className="w-full px-3 py-2 border border-[#c9cccf] dark:border-[#2e2e2e] rounded-lg bg-white dark:bg-[#1a1a1a] text-[#202223] dark:text-[#e3e3e3] focus:outline-none focus:ring-2 focus:ring-[#008060] dark:focus:ring-[#00a876]"
              rows={4}
              placeholder="Enter rejection reason..."
            />
            <div className="flex gap-2 mt-4">
              <button
                onClick={() => handleReject(showRejectModal)}
                disabled={actionLoading === showRejectModal}
                className="flex-1 px-4 py-2 bg-red-600 text-white rounded-lg hover:bg-red-700 disabled:opacity-50 transition-colors"
              >
                Confirm Reject
              </button>
              <button
                onClick={() => setShowRejectModal(null)}
                disabled={actionLoading === showRejectModal}
                className="flex-1 px-4 py-2 bg-gray-200 dark:bg-gray-700 text-gray-700 dark:text-gray-300 rounded-lg hover:bg-gray-300 dark:hover:bg-gray-600 transition-colors"
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
