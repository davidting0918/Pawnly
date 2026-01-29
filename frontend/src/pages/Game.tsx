import React, { useState, useEffect, useRef } from 'react';
import { Chess } from 'chess.js';
import { Chessboard } from 'react-chessboard';
import { useParams, useNavigate } from 'react-router-dom';
import { ArrowLeft, Copy, Wifi, WifiOff } from 'lucide-react';

const Game: React.FC = () => {
  const { id } = useParams<{ id: string }>();
  const navigate = useNavigate();
  const [game, setGame] = useState(new Chess());
  const [isConnected, setIsConnected] = useState(false);
  const ws = useRef<WebSocket | null>(null);

  useEffect(() => {
    // Connect to WebSocket
    const socket = new WebSocket(`ws://localhost:8000/ws/game/${id}`);
    
    socket.onopen = () => {
      console.log('Connected to game room');
      setIsConnected(true);
    };

    socket.onmessage = (event) => {
      const data = JSON.parse(event.data);
      
      if (data.type === 'init') {
        setGame(new Chess(data.fen));
      } else if (data.type === 'update') {
        setGame(new Chess(data.fen));
      } else if (data.type === 'error') {
        console.error(data.message);
      }
    };

    socket.onclose = () => setIsConnected(false);
    
    ws.current = socket;

    return () => {
      socket.close();
    };
  }, [id]);

  function onDrop(sourceSquare: string, targetSquare: string) {
    // Optimistic UI update (optional, but safer to wait for server or validate locally first)
    const movePayload = {
      type: 'move',
      from: sourceSquare,
      to: targetSquare
    };

    // Send to server
    if (ws.current && ws.current.readyState === WebSocket.OPEN) {
      ws.current.send(JSON.stringify(movePayload));
      // We don't update local state here; we wait for the server broadcast
      // OR we can try to move locally to validate logic before sending
      try {
          const tempGame = new Chess(game.fen());
          const move = tempGame.move({
              from: sourceSquare,
              to: targetSquare,
              promotion: 'q'
          });
          if (move) return true; // Allow piece to snap (react-chessboard needs this)
      } catch (e) {
          return false;
      }
    }
    return false;
  }

  return (
    <div className="min-h-screen bg-pawnly-dark flex flex-col items-center p-4">
      {/* Header */}
      <div className="w-full max-w-4xl flex justify-between items-center mb-8 text-white">
        <button onClick={() => navigate('/')} className="flex items-center gap-2 hover:text-pawnly-green">
          <ArrowLeft /> Leave
        </button>
        <div className="flex items-center gap-4 bg-pawnly-board px-4 py-2 rounded-full border border-gray-600">
          <span className="text-gray-400">Room Code:</span>
          <span className="font-mono font-bold text-xl">{id}</span>
          {isConnected ? <Wifi size={16} className="text-green-500" /> : <WifiOff size={16} className="text-red-500" />}
        </div>
        <div className="w-20"></div> {/* Spacer */}
      </div>

      <div className="flex flex-col md:flex-row gap-8 w-full max-w-5xl justify-center">
        {/* Board */}
        <div className="w-full max-w-[600px] aspect-square shadow-2xl rounded-lg overflow-hidden border-4 border-pawnly-board">
          <Chessboard 
            position={game.fen()} 
            onPieceDrop={onDrop}
            customDarkSquareStyle={{ backgroundColor: '#779954' }}
            customLightSquareStyle={{ backgroundColor: '#E9EDCC' }}
          />
        </div>

        {/* Sidebar */}
        <div className="w-full md:w-80 bg-pawnly-board rounded-lg p-4 border border-gray-700 flex flex-col h-[600px]">
          <div className="border-b border-gray-700 pb-4 mb-4">
            <h3 className="text-white font-bold text-lg mb-2">Players</h3>
            <div className="flex justify-between items-center bg-gray-800 p-2 rounded mb-2">
              <div className="flex items-center gap-2">
                <div className="w-3 h-3 rounded-full bg-white"></div>
                <span>You (White)</span>
              </div>
              <span className="text-gray-400">1200</span>
            </div>
            <div className="flex justify-between items-center bg-gray-800 p-2 rounded">
              <div className="flex items-center gap-2">
                <div className="w-3 h-3 rounded-full bg-black border border-gray-600"></div>
                <span>Opponent</span>
              </div>
              <span className="text-gray-400">1200</span>
            </div>
          </div>

          <div className="flex-1 overflow-y-auto">
            <h3 className="text-white font-bold text-lg mb-2 sticky top-0 bg-pawnly-board pb-2">Move History</h3>
            <div className="grid grid-cols-2 gap-2 text-sm">
              {/* Dummy Moves */}
              {game.history().map((move, index) => (
                <div key={index} className="flex gap-2 p-1 border-b border-gray-800">
                  <span className="text-gray-500 w-6">{Math.floor(index/2) + 1}.</span>
                  <span className={index % 2 === 0 ? "text-white" : "text-gray-300"}>{move}</span>
                </div>
              ))}
            </div>
          </div>
        </div>
      </div>
    </div>
  );
};

export default Game;
