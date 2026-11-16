import './Body.css';
import {useState} from "react";
import {useEffect} from "react";
import api from '../api.js'

const POSITIONS = {
    1: 'GK',
    2: 'DEF',
    3: 'MID',
    4: 'FWD'
}

function MainBody() {
  const [activeId, setActiveId] = useState(0);
  const [players, setPlayers] = useState([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState(null);

  useEffect(() => {
    // ignore responses from a filter the user has already clicked away from
    let cancelled = false;
    const fetchPlayers = async () => {
      setLoading(true);
      try {
        const response = await api.get("/", {
          params: {
            position: activeId
          }
        });
        if (!cancelled) {
          setPlayers(response.data);
          setError(null);
        }
      } catch (error) {
        console.error("Error fetching players", error);
        if (!cancelled) setError("Couldn't load predictions.");
      } finally {
        if (!cancelled) setLoading(false);
      }
    };
    fetchPlayers();
    return () => { cancelled = true; };
  }, [activeId]);

  return (
    <main className="body">
      <div className="section-head">
        <div>
          <h1 className="title">Top 10 projected scorers</h1>
          <p className="subtitle">Predicted points for the next gameweek</p>
        </div>
        <PositionFilter
          activeId={activeId}
          setActiveId={setActiveId}
        />
      </div>

      {error
        ? <p className="error">{error}</p>
        : <PlayerTable players={players} loading={loading} />}
    </main>
  );
}

function PositionFilter({ activeId, setActiveId }) {
    const buttons = [{id: 0, label: "All"}, ...Object.entries(POSITIONS).map(([id, label]) => ({id: Number(id), label}))];

    return (
        <div className="filter" role="group" aria-label="Filter by position">
            {buttons.map(btn => (
                <button
                    key={btn.id}
                    className="filter-button"
                    aria-pressed={activeId === btn.id}
                    onClick={() => setActiveId(btn.id)}
                >
                    {btn.label}
                </button>
            ))}
        </div>
    );
}

function PlayerTable({ players, loading }) {
    return (
        <div className={loading ? "table-wrap is-loading" : "table-wrap"}>
            <table className="player-table">
                <thead>
                    <tr>
                        <th className="col-rank">#</th>
                        <th>Player</th>
                        <th className="col-pos">Pos</th>
                        <th className="num col-price">Price</th>
                        <th className="num col-ict">ICT</th>
                        <th className="num">Last GW</th>
                        <th className="num col-pred">Projected</th>
                    </tr>
                </thead>
                <tbody>
                    {players.map((player, index) => (
                        <tr key={player["player_id"]}>
                            <td className="col-rank">{index + 1}</td>
                            <td>
                                <span className="player-name">{player["web_name"]}</span>
                                <span className="team">{player["short_name"]}</span>
                            </td>
                            <td className="col-pos">
                                <span className="pos">{POSITIONS[player["element_type"]]}</span>
                            </td>
                            <td className="num col-price">£{(player["now_cost"] / 10).toFixed(1)}m</td>
                            <td className="num col-ict">{Number(player["ict_index"]).toFixed(1)}</td>
                            <td className="num">{player["points_last_gw"]}</td>
                            <td className="num col-pred">
                                <span className="pred-value">{player["predicted_points"].toFixed(2)}</span>
                            </td>
                        </tr>
                    ))}
                </tbody>
            </table>
            {!loading && players.length === 0 && <p className="empty">No players to show.</p>}
        </div>
    );
}

export default MainBody;
