import { Wrench, Zap, Battery, Factory, ShieldCheck } from "lucide-react";
export function HeroNetwork() {
  return (
    <div
      className="hero-network"
      aria-label="A battery connects to assessment, reuse, second life and recovery"
    >
      <svg viewBox="0 0 600 430" aria-hidden="true">
        <defs>
          <pattern
            id="network-grid"
            width="30"
            height="30"
            patternUnits="userSpaceOnUse"
          >
            <circle cx="1" cy="1" r="1" fill="#cad1c4" />
          </pattern>
        </defs>
        <rect width="600" height="430" fill="url(#network-grid)" />
        <path
          className="network-track"
          d="M280 225 C340 225 305 95 445 95 M280 225 L445 225 M280 225 C335 225 310 355 445 355 M165 225 L245 225"
        />
        <path
          className="network-pulse"
          d="M165 225 L245 225 M280 225 C340 225 305 95 445 95 M280 225 L445 225 M280 225 C335 225 310 355 445 355"
        />
        <circle cx="270" cy="225" r="65" fill="#edf0e6" stroke="#cbd5c2" />
        <rect x="246" y="190" width="49" height="71" rx="9" fill="#194b36" />
        <rect x="260" y="183" width="22" height="8" rx="3" fill="#194b36" />
        <path
          d="M273 205 L260 226 L273 226 L265 245 L284 219 L271 219 Z"
          fill="#d8ef9a"
        />
        <circle cx="440" cy="95" r="6" fill="#698642" />
        <circle cx="440" cy="225" r="6" fill="#698642" />
        <circle cx="440" cy="355" r="6" fill="#698642" />
      </svg>
      <div className="network-source">
        <Wrench size={19} />
        <span>
          Workshop
          <br />
          <strong>Retired battery</strong>
        </span>
      </div>
      <div className="network-target t1">
        <Zap size={20} />
        <span>
          Continue use
          <br />
          <small>When requirements are met</small>
        </span>
      </div>
      <div className="network-target t2">
        <Battery size={20} />
        <span>
          Build a second life
          <br />
          <small>For a defined application</small>
        </span>
      </div>
      <div className="network-target t3">
        <Factory size={20} />
        <span>
          Recover materials
          <br />
          <small>Through eligible treatment</small>
        </span>
      </div>
      <div className="network-caption">
        <ShieldCheck size={16} /> Evidence guides the direction.
      </div>
    </div>
  );
}

