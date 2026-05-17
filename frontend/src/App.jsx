import { ThemeProvider, useTheme } from "./context/ThemeContext";
import { makeStyles } from "./styles/makeStyles";
import Sidebar from "./components/layout/Sidebar";
import Topbar from "./components/layout/Topbar";
import DashboardPage from "./pages/DashboardPage";

function Shell() {
  const { tokens: t } = useTheme();
  const s = makeStyles(t);

  return (
    <div style={s.root}>
      <Sidebar />
      <div style={s.main}>
        <Topbar />
        <DashboardPage />
      </div>
    </div>
  );
}

export default function App() {
  return (
    <ThemeProvider>
      <Shell />
    </ThemeProvider>
  );
}
