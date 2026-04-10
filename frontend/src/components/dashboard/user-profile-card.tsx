import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card';

interface UserProfileCardProps {
  user: {
    name: string;
    email: string;
    has_production_access?: boolean;
    can_post_to_production?: boolean;
  } | null;
}

export function UserProfileCard({ user }: UserProfileCardProps) {
  if (!user) return null;

  return (
    <Card>
      <CardHeader>
        <CardTitle className="text-lg font-bold text-[#202223] dark:text-[#e3e3e3]">Your Profile</CardTitle>
      </CardHeader>
      <CardContent className="space-y-4">
        <div>
          <p className="text-sm font-semibold text-[#6d7175] dark:text-[#8c9196]">Name</p>
          <p className="text-base font-semibold text-[#202223] dark:text-[#e3e3e3]">{user.name}</p>
        </div>
        <div>
          <p className="text-sm font-semibold text-[#6d7175] dark:text-[#8c9196]">Email</p>
          <p className="text-base text-[#202223] dark:text-[#e3e3e3]">{user.email}</p>
        </div>
        <div className="pt-4 border-t border-[#e1e3e5] dark:border-[#2e2e2e]">
          <p className="text-sm font-semibold text-[#6d7175] dark:text-[#8c9196] mb-2">Permissions</p>
          <div className="space-y-2">
            <div className="flex items-center">
              {user.has_production_access ? (
                <>
                  <svg className="h-5 w-5 text-[#008060] dark:text-[#00a876] mr-2" fill="currentColor" viewBox="0 0 20 20">
                    <path fillRule="evenodd" d="M10 18a8 8 0 100-16 8 8 0 000 16zm3.707-9.293a1 1 0 00-1.414-1.414L9 10.586 7.707 9.293a1 1 0 00-1.414 1.414l2 2a1 1 0 001.414 0l4-4z" clipRule="evenodd" />
                  </svg>
                  <span className="text-sm text-[#202223] dark:text-[#e3e3e3]">Production Access</span>
                </>
              ) : (
                <>
                  <svg className="h-5 w-5 text-[#8c9196] dark:text-[#6d7175] mr-2" fill="currentColor" viewBox="0 0 20 20">
                    <path fillRule="evenodd" d="M10 18a8 8 0 100-16 8 8 0 000 16zM8.707 7.293a1 1 0 00-1.414 1.414L8.586 10l-1.293 1.293a1 1 0 101.414 1.414L10 11.414l1.293 1.293a1 1 0 001.414-1.414L11.414 10l1.293-1.293a1 1 0 00-1.414-1.414L10 8.586 8.707 7.293z" clipRule="evenodd" />
                  </svg>
                  <span className="text-sm text-[#6d7175] dark:text-[#8c9196]">Production Access (Pending)</span>
                </>
              )}
            </div>
            <div className="flex items-center">
              {user.can_post_to_production ? (
                <>
                  <svg className="h-5 w-5 text-[#008060] dark:text-[#00a876] mr-2" fill="currentColor" viewBox="0 0 20 20">
                    <path fillRule="evenodd" d="M10 18a8 8 0 100-16 8 8 0 000 16zm3.707-9.293a1 1 0 00-1.414-1.414L9 10.586 7.707 9.293a1 1 0 00-1.414 1.414l2 2a1 1 0 001.414 0l4-4z" clipRule="evenodd" />
                  </svg>
                  <span className="text-sm text-[#202223] dark:text-[#e3e3e3]">Can Post to Production</span>
                </>
              ) : (
                <>
                  <svg className="h-5 w-5 text-[#8c9196] dark:text-[#6d7175] mr-2" fill="currentColor" viewBox="0 0 20 20">
                    <path fillRule="evenodd" d="M10 18a8 8 0 100-16 8 8 0 000 16zM8.707 7.293a1 1 0 00-1.414 1.414L8.586 10l-1.293 1.293a1 1 0 101.414 1.414L10 11.414l1.293 1.293a1 1 0 001.414-1.414L11.414 10l1.293-1.293a1 1 0 00-1.414-1.414L10 8.586 8.707 7.293z" clipRule="evenodd" />
                  </svg>
                  <span className="text-sm text-[#6d7175] dark:text-[#8c9196]">Post to Production (Restricted)</span>
                </>
              )}
            </div>
          </div>
        </div>
      </CardContent>
    </Card>
  );
}
