"use client";

import { Component, ReactNode, ErrorInfo } from "react";

interface Props {
  children: ReactNode;
  fallback?: ReactNode;
}

interface State {
  hasError: boolean;
  error: Error | null;
}

export class ErrorBoundary extends Component<Props, State> {
  constructor(props: Props) {
    super(props);
    this.state = { hasError: false, error: null };
  }

  static getDerivedStateFromError(error: Error): State {
    return { hasError: true, error };
  }

  componentDidCatch(error: Error, info: ErrorInfo) {
    console.error("[ErrorBoundary]", error, info.componentStack);
  }

  handleRetry = () => {
    this.setState({ hasError: false, error: null });
  };

  render() {
    if (this.state.hasError) {
      if (this.props.fallback) return this.props.fallback;
      return (
        <div className="flex flex-col items-center justify-center min-h-[200px] gap-4 p-8 text-center">
          <p className="text-zinc-400 text-sm">Something went wrong.</p>
          {this.state.error && (
            <pre className="text-zinc-500 text-xs bg-zinc-900 rounded p-3 max-w-md overflow-auto">
              {this.state.error.message}
            </pre>
          )}
          <button
            onClick={this.handleRetry}
            className="px-4 py-2 rounded-md bg-zinc-800 text-zinc-200 text-sm hover:bg-zinc-700 transition-colors"
          >
            Try again
          </button>
        </div>
      );
    }
    return this.props.children;
  }
}
