export default function AuthLayout({
  children,
}: {
  children: React.ReactNode;
}) {
  return (
    <div className="min-h-screen flex items-center justify-center bg-[#f5f5f4] dark:bg-[#0a0a0a] py-12 px-4 sm:px-6 lg:px-8">
      {children}
    </div>
  );
}