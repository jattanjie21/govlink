import { Routes, Route } from "react-router-dom";
import SiteLayout from "@/layouts/SiteLayout";
import Home from "@/routes/Home";
import Browse from "@/routes/Browse";
import DatasetLayout from "@/routes/dataset/DatasetLayout";
import DatasetOverview from "@/routes/dataset/Overview";
import DatasetPreview from "@/routes/dataset/Preview";
import DatasetApi from "@/routes/dataset/Api";
import Operator from "@/routes/Operator";
import Placeholder from "@/routes/Placeholder";

export default function App() {
  return (
    <Routes>
      <Route element={<SiteLayout />}>
        <Route index element={<Home />} />
        <Route path="/datasets" element={<Browse />} />

        <Route path="/datasets/:slug" element={<DatasetLayout />}>
          <Route index element={<DatasetOverview />} />
          <Route path="preview" element={<DatasetPreview />} />
          <Route path="api" element={<DatasetApi />} />
        </Route>

        <Route path="/operator" element={<Operator />} />
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
