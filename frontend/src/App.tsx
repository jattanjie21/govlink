import { Routes, Route } from "react-router-dom";
import SiteLayout from "@/layouts/SiteLayout";
import HomeStub from "@/routes/HomeStub";
import Placeholder from "@/routes/Placeholder";

export default function App() {
  return (
    <Routes>
      <Route element={<SiteLayout />}>
        <Route index element={<HomeStub />} />
        <Route
          path="/datasets"
          element={<Placeholder title="Browse datasets" step="Step 5" />}
        />
        <Route
          path="/datasets/:slug"
          element={<Placeholder title="Dataset detail" step="Step 6" />}
        />
        <Route
          path="/datasets/:slug/api"
          element={<Placeholder title="Dataset API" step="Step 7" />}
        />
        <Route
          path="/operator"
          element={<Placeholder title="Operator health" step="Step 8" />}
        />
        <Route
          path="/api-docs"
          element={<Placeholder title="API documentation" step="Step 7" />}
        />
        <Route
          path="*"
          element={<Placeholder title="Page not found (404)" step="Step 9" />}
        />
      </Route>
    </Routes>
  );
}
