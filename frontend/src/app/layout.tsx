import type { Metadata } from "next";
import { Inter } from "next/font/google";
import "./globals.css";
import { SidebarNav } from "@/components/sidebar-nav";
import { DataSidebar, MobileDataSidebar } from "@/components/data-sidebar";
import { ErrorBoundary } from "@/components/error-boundary";
import { Providers } from "@/components/providers";

const inter = Inter({
  subsets: ["latin"],
  variable: "--font-inter",
});

export const metadata: Metadata = {
  title: "RSSFeed2",
  description: "RSS aggregator with NLP pipeline",
};

export default function RootLayout({
  children,
}: Readonly<{
  children: React.ReactNode;
}>) {
  return (
    <html lang="en" className="dark">
      <body className={`${inter.variable} font-sans antialiased bg-zinc-950 text-zinc-100`}>
        <Providers>
          <ErrorBoundary>
            <div className="flex min-h-screen">
              <SidebarNav />
              <main className="flex-1 min-w-0 overflow-y-auto">{children}</main>
              <DataSidebar />
              <MobileDataSidebar />
            </div>
          </ErrorBoundary>
        </Providers>
      </body>
    </html>
  );
}
