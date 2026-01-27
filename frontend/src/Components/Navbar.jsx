import { useState } from "react";
import './Navbar.css';

function NavBar() {
  const [open, setOpen] = useState(false);

  return (
    <nav className="navbar">
      <div className="nav-header">
        <button
          className="list-button"
          onClick={() => setOpen(prev => !prev)}
        >
          ☰
        </button>
        <div className="page-title">
          <h1>FPL ML Predictor</h1>
        </div>
      </div>

      {open && <NavList />}
    </nav>
  );
}

function NavList() {
  return (
    <ul className="menu-list">
      <li>About</li>
      <li>Top 10 Scorers</li>
      <li>Past Gameweek Predictions</li>
      <li>Model Info</li>
    </ul>
  );
}

export default NavBar;
