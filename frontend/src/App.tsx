import { BackgroundRippleEffect } from "@/components/ui/background-ripple-effect";
import AppRouter from "@/routes/AppRouter";

function App() {
  return (
    <main className="dark relative min-h-screen overflow-hidden bg-black text-white">
      <BackgroundRippleEffect cols={22} opacity={30} rows={7} />
      <div className="relative z-10 min-h-screen w-full">
        <AppRouter />
      </div>
    </main>
  );
}

export default App;
