import { Route, Routes } from "react-router-dom";
import { RootLayout } from "./layouts/RootLayout/RootLayout";
import { Dashboard } from "./pages/Dashboard/Dashboard";

export function AppRouter() {
  return (
    <Routes>
      <Route element={<RootLayout />}>
        <Route path="/" element={<Dashboard />} />
      </Route>
    </Routes>
  );
}
