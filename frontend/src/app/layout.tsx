import type { Metadata } from "next";
import "./globals.css";
import { SidebarNav } from "@/components/sidebar-nav";
import { DataSidebar, MobileDataSidebar } from "@/components/data-sidebar";
import { ErrorBoundary } from "@/components/error-boundary";
import { Providers } from "@/components/providers";

export const metadata: Metadata = {
  title: "SiftSignal",
  description: "Financial news intelligence platform",
};

export default function RootLayout({
  children,
}: Readonly<{
  children: React.ReactNode;
}>) {
  return (
    <html lang="en" className="dark">
      <body className="antialiased bg-background text-foreground">
        <Providers>
          <ErrorBoundary>
            <div className="flex min-h-screen">
              <SidebarNav />
              <main className="flex-1 min-w-0 overflow-y-auto pt-14 lg:pt-0">{children}</main>
              <DataSidebar />
              <MobileDataSidebar />
            </div>
          </ErrorBoundary>
        </Providers>
      </body>
    </html>
  );
}
