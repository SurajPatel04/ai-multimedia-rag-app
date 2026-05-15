import { BackgroundRippleEffect } from "@/components/ui/background-ripple-effect";
import AppRouter from "@/routes/AppRouter";
import { ToastContainer } from "react-toastify";
import "react-toastify/dist/ReactToastify.css";

function App() {
  return (
    <main className="dark relative min-h-screen overflow-hidden bg-black text-white">
      <BackgroundRippleEffect cols={22} opacity={30} rows={7} />
      <div className="relative z-10 min-h-screen w-full">
        <AppRouter />
      </div>
      <ToastContainer
        position="top-right"
        autoClose={3000}
        hideProgressBar={false}
        newestOnTop={false}
        closeOnClick
        rtl={false}
        pauseOnFocusLoss
        draggable
        pauseOnHover
        theme="dark"
      />
    </main>
  );
}

export default App;
