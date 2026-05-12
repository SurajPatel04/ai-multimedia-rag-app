import { BackgroundRippleEffect } from "@/components/ui/background-ripple-effect";
import AppRouter from "@/routes/AppRouter";

function App() {
  return (
    <main className="dark relative min-h-screen overflow-hidden bg-black px-4 py-10 text-white">
      <BackgroundRippleEffect />
      <div className="relative z-10 mx-auto min-h-[calc(100vh-5rem)] w-full">
        <AppRouter />
      </div>
    </main>
  );
}

export default App;
