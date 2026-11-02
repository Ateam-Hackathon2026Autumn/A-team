import { Component, type ErrorInfo, type ReactNode } from 'react';

type ErrorBoundaryProps = {
  children: ReactNode;
};

type ErrorBoundaryState = {
  hasError: boolean;
};

// 予期せぬエラーで画面が真っ白になるのを防ぐ
class ErrorBoundary extends Component<ErrorBoundaryProps, ErrorBoundaryState> {
  state: ErrorBoundaryState = { hasError: false };

  static getDerivedStateFromError(): ErrorBoundaryState {
    return { hasError: true };
  }

  componentDidCatch(error: Error, errorInfo: ErrorInfo) {
    console.error('画面の描画中にエラーが発生しました。', error, errorInfo);
  }

  handleGoToHome = () => {
    window.location.assign('/');
  };

  render() {
    if (!this.state.hasError) {
      return this.props.children;
    }

    return (
      <div className="flex min-h-dvh items-center justify-center bg-[#f4f5f0] px-5">
        <div className="w-full max-w-[440px] text-center">
          <h2 className="text-xl font-bold text-[#26332b]">
            予期せぬエラーが発生しました
          </h2>
          <p className="mt-2 text-sm leading-relaxed text-[#5b675f]">
            画面を表示できませんでした。
            <br />
            お手数ですが、はじめからやり直してください。
          </p>
          <button
            type="button"
            className="mt-5 w-full rounded-full border-0 bg-[#2f6b4f] px-6 py-3 font-bold text-white"
            onClick={this.handleGoToHome}
          >
            ホームへ
          </button>
        </div>
      </div>
    );
  }
}

export default ErrorBoundary;
