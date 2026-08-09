export default function App() {
  return (
    <div className="grid h-screen grid-cols-[300px_1fr_340px] gap-4 bg-slate-50 p-4">
      <aside className="rounded-xl bg-white p-4 shadow-sm">
        Panel: Paciente
      </aside>
      <main className="rounded-xl bg-white p-4 shadow-sm">
        Panel: Conversación
      </main>
      <aside className="rounded-xl bg-white p-4 shadow-sm">
        Panel: Inteligencia
      </aside>
    </div>
  );
}
