  );

  const totalCountries = COUNTRIES_IN_THE_WORLD;

  // Read Mapbox public token from environment.
  // Accepts either the Mapbox connector's injected token or a manually set env var.
  // Public tokens (pk.*) are designed for client-side use and should be URL-restricted
  // in the Mapbox dashboard to your domains for quota protection.
  const getMapboxToken = (): string | null => {
    const token =
      import.meta.env.VITE_LOVABLE_CONNECTOR_MAPBOX_PUBLIC_TOKEN ||
      import.meta.env.VITE_MAPBOX_PUBLIC_KEY;
    if (!token) {
      console.error('MapboxWorldMap: no Mapbox public token found in environment');
      return null;
    }
    return token;
  };


  /**
