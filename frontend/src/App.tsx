import { BackgroundRippleEffect } from "@/components/ui/background-ripple-effect";
import LoginPage from "@/pages/LoginPage";
import MePage from "@/pages/MePage";
import SignupPage from "@/pages/SignupPage";

function App() {
  const path = window.location.pathname;
  let page = <LoginPage />;

  if (path === "/signup" || path === "/register") {
    page = <SignupPage />;
  }

  if (path === "/me" || path === "/user/me" || path === "/dashboard") {
    page = <MePage />;
  }

  return (
    <main className="dark relative min-h-screen overflow-hidden bg-black px-4 py-10 text-white">
      <BackgroundRippleEffect />
      <div className="relative z-10 mx-auto min-h-[calc(100vh-5rem)] w-full">
        {page}
      </div>
    </main>
  );
}

export default App;
