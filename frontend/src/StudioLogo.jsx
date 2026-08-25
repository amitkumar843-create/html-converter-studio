import React from "react";

export default function StudioLogo({ size = 38, className = "" }) {
  return (
    <svg
      width={size}
      height={size}
      viewBox="0 0 48 48"
      fill="none"
      xmlns="http://www.w3.org/2000/svg"
      className={className}
    >
      <defs>
        {/* Background Tile Gradient */}
        <linearGradient id="logoBgGrad" x1="0%" y1="0%" x2="100%" y2="100%">
          <stop offset="0%" stopColor="#4F46E5" />
          <stop offset="50%" stopColor="#7C3AED" />
          <stop offset="100%" stopColor="#06B6D4" />
        </linearGradient>

        {/* Back Slide Gradient */}
        <linearGradient id="backSlideGrad" x1="0%" y1="0%" x2="100%" y2="100%">
          <stop offset="0%" stopColor="#8B5CF6" stopOpacity="0.8" />
          <stop offset="100%" stopColor="#6366F1" stopOpacity="0.5" />
        </linearGradient>

        {/* Front Slide Glass Gradient */}
        <linearGradient id="frontSlideGrad" x1="0%" y1="0%" x2="100%" y2="100%">
          <stop offset="0%" stopColor="#FFFFFF" stopOpacity="0.98" />
          <stop offset="100%" stopColor="#F0F9FF" stopOpacity="0.9" />
        </linearGradient>

        {/* Code Accent Gradient */}
        <linearGradient id="codeGrad" x1="0%" y1="0%" x2="100%" y2="100%">
          <stop offset="0%" stopColor="#4F46E5" />
          <stop offset="100%" stopColor="#0891B2" />
        </linearGradient>
      </defs>

      {/* Main App Squircle Frame */}
      <rect
        x="2"
        y="2"
        width="44"
        height="44"
        rx="13"
        fill="url(#logoBgGrad)"
      />
      <rect
        x="2"
        y="2"
        width="44"
        height="44"
        rx="13"
        stroke="rgba(255, 255, 255, 0.4)"
        strokeWidth="1.5"
      />

      {/* Back Layered Presentation Slide */}
      <rect
        x="16"
        y="8.5"
        width="22"
        height="17"
        rx="3.5"
        fill="url(#backSlideGrad)"
        stroke="rgba(255, 255, 255, 0.4)"
        strokeWidth="1"
      />

      {/* Mid Layered Presentation Slide */}
      <rect
        x="11"
        y="13.5"
        width="23"
        height="18"
        rx="4"
        fill="rgba(15, 23, 42, 0.7)"
        stroke="rgba(147, 197, 253, 0.6)"
        strokeWidth="1.2"
      />

      {/* Front Frosted Presentation Slide */}
      <rect
        x="7.5"
        y="18"
        width="25"
        height="19.5"
        rx="4.5"
        fill="url(#frontSlideGrad)"
        stroke="#FFFFFF"
        strokeWidth="1.2"
      />

      {/* Code Brackets on Front Slide: < / > */}
      {/* Left Bracket < */}
      <path
        d="M15 24.5L12 27.5L15 30.5"
        stroke="url(#codeGrad)"
        strokeWidth="2.4"
        strokeLinecap="round"
        strokeLinejoin="round"
      />

      {/* Slash / */}
      <path
        d="M20.5 23.5L18.5 31.5"
        stroke="url(#codeGrad)"
        strokeWidth="2.2"
        strokeLinecap="round"
      />

      {/* Right Bracket > */}
      <path
        d="M24 24.5L27 27.5L24 30.5"
        stroke="url(#codeGrad)"
        strokeWidth="2.4"
        strokeLinecap="round"
        strokeLinejoin="round"
      />

      {/* Magic Sparkle Star in Top Right */}
      <path
        d="M37 11C37 13.2 38.8 15 41 15C38.8 15 37 16.8 37 19C37 16.8 35.2 15 33 15C35.2 15 37 13.2 37 11Z"
        fill="#FDE047"
      />
      <circle cx="37" cy="15" r="1.2" fill="#FFFFFF" />
    </svg>
  );
}
