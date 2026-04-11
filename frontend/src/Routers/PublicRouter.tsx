import careConfig from "@careConfig";
import { Redirect, useRoutes } from "raviger";

import { Authenticate } from "@/components/Auth/Authenticate";
import Login from "@/components/Auth/Login";
import ResetPassword from "@/components/Auth/ResetPassword";
import BrowserWarning from "@/components/ErrorPages/BrowserWarning";
import InvalidReset from "@/components/ErrorPages/InvalidReset";
import SessionExpired from "@/components/ErrorPages/SessionExpired";
import { useTenantContext } from "@/context/TenantContext";

import { FacilitiesPage } from "@/pages/Facility/FacilitiesPage";
import { FacilityDetailsPage } from "@/pages/Facility/FacilityDetailsPage";
import { LandingPage } from "@/pages/Landing/LandingPage";
import { LicensesPage } from "@/pages/Licenses/Licenses";
import PatientLogin from "@/pages/PublicAppointments/auth/PatientLogin";

export const routes = {
  "/": () =>
    careConfig.disablePatientLogin ? <Redirect to="/login" /> : <LandingPage />,
  "/facilities": () =>
    careConfig.disablePatientLogin ? (
      <Redirect to="/login" />
    ) : (
      <FacilitiesPage />
    ),
  "/facility/:id": ({ id }: { id: string }) =>
    careConfig.disablePatientLogin ? (
      <Redirect to="/login" />
    ) : (
      <FacilityDetailsPage id={id} />
    ),
  "/facility/:facilityId/appointments/:staffId/otp/:page": ({
    facilityId,
    staffId,
    page,
  }: {
    facilityId: string;
    staffId: string;
    page: string;
  }) =>
    careConfig.disablePatientLogin ? (
      <Redirect to="/login" />
    ) : (
      <PatientLogin facilityId={facilityId} staffId={staffId} page={page} />
    ),
  "/login": () => <Login />,
  "/2fa": () => <Authenticate />,
  "/forgot-password": () => <Login forgot={true} />,
  "/password_reset/:token": ({ token }: { token: string }) => (
    <ResetPassword token={token} />
  ),
  "/session-expired": () => <SessionExpired />,
  "/licenses": () => <LicensesPage />,
  "/invalid-reset": () => <InvalidReset />,
};

export default function PublicRouter() {
  const tenant = useTenantContext();
  const routeResult = useRoutes(routes);
  const isAppSubdomain =
    window.location.hostname.toLowerCase() === "app.parxio.in" &&
    window.location.pathname === "/";
  const content = isAppSubdomain
    ? <Login />
    : routeResult
      ? routeResult
      : tenant.is_admin_host
        ? <Login />
        : <Redirect to="/login" />;

  return (
    <>
      <BrowserWarning />
      {content}
    </>
  );
}
