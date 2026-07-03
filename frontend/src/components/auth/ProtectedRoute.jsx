// GUEST MODE — auth guard disabled for demo/portfolio access.
// To re-enable: uncomment the block below and remove the `return children` line.
//
// import { Navigate, useLocation } from "react-router-dom";
// import useAuthStore from "../../store/useAuthStore";
// export default function ProtectedRoute({ children }) {
//   const isAuthenticated = useAuthStore((s) => s.isAuthenticated);
//   const location = useLocation();
//   if (!isAuthenticated) {
//     return <Navigate to="/login" state={{ from: location }} replace />;
//   }
//   return children;
// }

export default function ProtectedRoute({ children }) {
  return children;
}
