import { Component, type ErrorInfo, type ReactNode } from "react";

/** Contains a render error to one section: shows a message instead of blanking the whole site. */
export class SectionBoundary extends Component<{ name: string; children: ReactNode }, { error: Error | null }> {
  state = { error: null as Error | null };

  static getDerivedStateFromError(error: Error) {
    return { error };
  }

  componentDidCatch(error: Error, info: ErrorInfo) {
    // keep a diagnosable trace in the console (component stack included)
    console.error(`[${this.props.name}] ${error.message}`, info.componentStack);
  }

  render() {
    if (this.state.error) {
      return (
        <div className="state error" role="alert">
          <div>
            This part of the page could not be displayed ({this.state.error.message}).{" "}
            <button className="btn small" onClick={() => this.setState({ error: null })}>Try again</button>
          </div>
        </div>
      );
    }
    return this.props.children;
  }
}
