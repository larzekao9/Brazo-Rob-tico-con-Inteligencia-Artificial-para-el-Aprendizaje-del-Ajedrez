import Partida from "./components/Partida.jsx";
import ConsolaMotor from "./components/ConsolaMotor.jsx";

export default function App() {
  return (
    <div className="taller">
      <header className="cabecera">
        <p className="marca">Brazo Robótico de Ajedrez</p>
        <p className="submarca">Stockfish decide la jugada · simulación de brazo en curso</p>
      </header>

      <main className="banco">
        <Partida />
        <ConsolaMotor />
      </main>
    </div>
  );
}
