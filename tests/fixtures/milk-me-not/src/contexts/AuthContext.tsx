    // fact about props, so it belongs in an effect.
    // eslint-disable-next-line react-hooks/set-state-in-effect
    setLoading(true);
    
    // If the URL contains a recovery hash, mark recovery mode early.
    // (Some environments provide access_token but an empty refresh_token; event may not fire.)
    try {
      const hashParams = new URLSearchParams(window.location.hash.substring(1));
      const type = hashParams.get('type');
      const accessToken = hashParams.get('access_token');
      if (type === 'recovery' && accessToken) {
        sessionStorage.setItem('passwordRecoveryMode', 'true');
        sessionStorage.setItem('passwordRecoveryAccessToken', accessToken);
      }
    } catch {
      // ignore
    }

    // Set up auth state listener FIRST
    const { data: { subscription } } = supabase.auth.onAuthStateChange(
      async (event, session) => {
