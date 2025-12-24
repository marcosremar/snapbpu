import React from 'react';
import { VectorMap } from '@react-jvectormap/core';
import { worldMill } from '@react-jvectormap/world';
import { useTheme } from '../../context/ThemeContext';

const WorldMap = ({ selectedCodes = [], onCountryClick }) => {
  const { theme } = useTheme();
  const isDark = theme === 'dark';

  // Theme-aware colors usando paleta TailAdmin (Material Green)
  const mapColors = {
    dark: {
      background: 'rgb(17, 24, 39)', // gray-900
      landFill: 'rgb(31, 41, 55)', // gray-800
      landStroke: 'rgb(55, 65, 81)', // gray-700
      hoverFill: 'rgb(46, 125, 50)', // brand-800
      hoverStroke: 'rgb(76, 175, 80)', // brand-500
      selectedFill: 'rgb(46, 125, 50)', // brand-800
      markerFill: 'rgb(76, 175, 80)', // brand-500
      markerStroke: 'rgb(129, 199, 132)', // brand-300
    },
    light: {
      background: 'rgb(249, 250, 251)', // gray-50
      landFill: 'rgb(229, 231, 235)', // gray-200
      landStroke: 'rgb(209, 213, 219)', // gray-300
      hoverFill: 'rgb(46, 125, 50)', // brand-800
      hoverStroke: 'rgb(76, 175, 80)', // brand-500
      selectedFill: 'rgb(46, 125, 50)', // brand-800
      markerFill: 'rgb(46, 125, 50)', // brand-800
      markerStroke: 'rgb(76, 175, 80)', // brand-500
    }
  };

  const colors = isDark ? mapColors.dark : mapColors.light;

  // Datacenter markers
  const datacenterMarkers = [
    { latLng: [37.77, -122.42], name: 'San Francisco', code: 'US' },
    { latLng: [40.71, -74.01], name: 'New York', code: 'US' },
    { latLng: [51.51, -0.13], name: 'London', code: 'GB' },
    { latLng: [48.86, 2.35], name: 'Paris', code: 'FR' },
    { latLng: [52.52, 13.40], name: 'Berlin', code: 'DE' },
    { latLng: [35.68, 139.69], name: 'Tokyo', code: 'JP' },
    { latLng: [1.35, 103.82], name: 'Singapore', code: 'SG' },
    { latLng: [-23.55, -46.63], name: 'São Paulo', code: 'BR' },
  ];

  // Filter markers based on selected codes
  const visibleMarkers = selectedCodes.length === 0
    ? datacenterMarkers
    : datacenterMarkers.filter(m => selectedCodes.includes(m.code));

  return (
    <div className={`relative w-full h-full ${isDark ? 'bg-gray-900' : 'bg-gray-50'}`}>
      <VectorMap
        key={`map-${theme}`}
        map={worldMill}
        backgroundColor="transparent"
        containerStyle={{
          width: '100%',
          height: '100%',
        }}
        markerStyle={{
          initial: {
            fill: colors.markerFill,
            r: 6,
            stroke: colors.markerStroke,
            strokeWidth: 2,
            fillOpacity: 0.9,
          },
          hover: {
            fill: colors.hoverFill,
            r: 8,
            stroke: colors.hoverStroke,
            strokeWidth: 2,
            fillOpacity: 1,
          },
        }}
        markers={visibleMarkers.map(m => ({
          latLng: m.latLng,
          name: m.name,
          style: { fill: colors.markerFill, stroke: colors.markerStroke, strokeWidth: 2, fillOpacity: 0.9 },
        }))}
        zoomOnScroll={false}
        zoomMax={12}
        zoomMin={1}
        onRegionClick={(e, code) => {
          if (onCountryClick) {
            onCountryClick(code);
          }
        }}
        regionStyle={{
          initial: {
            fill: colors.landFill,
            fillOpacity: 1,
            stroke: colors.landStroke,
            strokeWidth: 0.5,
            strokeOpacity: 1,
          },
          hover: {
            fillOpacity: 0.9,
            cursor: 'pointer',
            fill: colors.hoverFill,
            stroke: colors.hoverStroke,
            strokeWidth: 1,
          },
        }}
        series={{
          regions: [{
            values: selectedCodes.reduce((acc, code) => {
              acc[code] = 1;
              return acc;
            }, {}),
            scale: {
              '1': colors.selectedFill
            },
            attribute: 'fill'
          }]
        }}
      />
    </div>
  );
};

export default WorldMap;
