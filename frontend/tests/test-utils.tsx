import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import { render, RenderOptions } from "@testing-library/react";
import { BrowserRouter } from "react-router-dom";
import { ReactElement } from "react";

function createTestQueryClient() {
  return new QueryClient({
    defaultOptions: {
      queries: { retry: false },
      mutations: { retry: false },
    },
  });
}

interface WrapperOptions {
  queryClient?: QueryClient;
}

function createWrapper(options: WrapperOptions = {}) {
  const { queryClient = createTestQueryClient() } = options;

  return function Wrapper({ children }: { children: React.ReactNode }) {
    return (
      <QueryClientProvider client={queryClient}>
        <BrowserRouter>{children}</BrowserRouter>
      </QueryClientProvider>
    );
  };
}

export function renderWithProviders(
  ui: ReactElement,
  options: RenderOptions & WrapperOptions = {},
) {
  const { queryClient, ...renderOptions } = options;
  const wrapper = createWrapper({ queryClient });

  return { ...render(ui, { wrapper, ...renderOptions }) };
}

export { createTestQueryClient };
