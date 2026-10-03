import { TooltipProvider } from "@/components/ui/tooltip";
import { Toaster } from "@/components/ui/toaster";
import { Toaster as Sonner } from "@/components/ui/sonner";
import { ProductionErrorBoundary } from "@/components/ui/production-error-boundary";
import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import { BrowserRouter, Routes, Route } from "react-router-dom";
import { I18nextProvider } from "react-i18next";
import { Suspense } from "react";
import i18n from "./i18n/config";
import Index from "./pages/Index";
import Auth from "./pages/Auth";
import DepartmentDetail from "./pages/DepartmentDetail";
import NotFound from "./pages/NotFound";
import Admin from "./pages/Admin";
import ContactTest from "./pages/ContactTest";
import Scenarios from "./pages/Scenarios";
import ScenarioDetail from "./pages/ScenarioDetail";
import DemoComingSoon from "./pages/DemoComingSoon";
import Donations from "./pages/Donations";
import DonationSuccess from "./pages/DonationSuccess";
import DonationCancel from "./pages/DonationCancel";
import WorkPackages from "./pages/WorkPackages";
import SiteAudit from "./pages/SiteAudit";
import FreeCourses from "./pages/FreeCourses";
import WorkFamilyAICourse from "./pages/WorkFamilyAICourse";
import Contact from "./pages/Contact";
import { OrganizationalDashboard } from "./components/organizational/OrganizationalDashboard";
import { CompleteOrganizationalStructure } from "./components/organizational/CompleteOrganizationalStructure";
import { NavigationHeader } from "./components/ui/navigation-header";
import { ProtectedRoute } from "./components/auth/ProtectedRoute";

const queryClient = new QueryClient({
  defaultOptions: {
    queries: {
      retry: 2,
      staleTime: 5 * 60 * 1000,
      gcTime: 10 * 60 * 1000,
    },
  },
});

const LoadingFallback = () => (
  <div className="min-h-screen bg-gradient-to-br from-slate-50 via-blue-50 to-indigo-100 flex items-center justify-center">
    <div className="text-center">
      <div className="animate-spin rounded-full h-8 w-8 border-b-2 border-blue-600 mx-auto mb-4"></div>
      <p className="text-gray-600">Loading...</p>
    </div>
  </div>
);

const App = () => {
  return (
    <ProductionErrorBoundary>
      <I18nextProvider i18n={i18n}>
        <QueryClientProvider client={queryClient}>
          <TooltipProvider>
            <Toaster />
            <Sonner />
            <BrowserRouter>
              <NavigationHeader />
              <Suspense fallback={<LoadingFallback />}>
                <Routes>
                  <Route path="/" element={<Index />} />
                  <Route path="/auth" element={<Auth />} />
                  <Route path="/free-courses" element={<FreeCourses />} />
                  <Route path="/free-courses/workfamily-ai-foundations" element={<WorkFamilyAICourse />} />
                  <Route path="/work-packages" element={<WorkPackages />} />
                  <Route path="/department/:departmentId" element={<DepartmentDetail />} />
                  <Route path="/admin" element={<ProtectedRoute requireAdmin={true}><Admin /></ProtectedRoute>} />
                  <Route path="/contact-test" element={<ContactTest />} />
                  <Route path="/scenarios" element={<Scenarios />} />
                  <Route path="/scenarios/:scenarioId" element={<ScenarioDetail />} />
                  <Route path="/demo" element={<DemoComingSoon />} />
                  <Route path="/donations" element={<Donations />} />
                  <Route path="/donation-success" element={<DonationSuccess />} />
                  <Route path="/donation-cancel" element={<DonationCancel />} />
                  <Route path="/site-audit" element={<SiteAudit />} />
                  <Route path="/contact" element={<Contact />} />
                  <Route path="/organizational-intelligence" element={<OrganizationalDashboard />} />
                  <Route path="/complete-structure" element={<CompleteOrganizationalStructure />} />
                  <Route path="*" element={<NotFound />} />
                </Routes>
              </Suspense>
            </BrowserRouter>
          </TooltipProvider>
        </QueryClientProvider>
      </I18nextProvider>
    </ProductionErrorBoundary>
  );
};

export default App;
