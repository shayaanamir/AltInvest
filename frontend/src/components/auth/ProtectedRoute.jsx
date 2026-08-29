import { Navigate, useLocation } from "react-router-dom";
import { isAuthenticated } from "../../hooks/useAuth";

export default function ProtectedRoute({ children }) {
    const location = useLocation();

    if (!isAuthenticated()) {
        const returnPath = location.pathname + location.search;
        return <Navigate to={`/login?return=${encodeURIComponent(returnPath)}`} replace />;
    }

    return children;
}