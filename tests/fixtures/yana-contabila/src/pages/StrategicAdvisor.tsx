  }, [userProfile, welcomeMessageShown, messages.length, isMobile, mobileWarningShown, emotionalContext]);

  // Check access and credit on mount
  useEffect(() => {
    const checkAccessAndCredit = async () => {
      // Așteptăm să știm dacă avem sesiune sau nu
      if (!sessionChecked) {
        logger.log("⏳ [ACCESS-CHECK] Waiting for session check...");
        return;
      }
      
      // Dacă sesiunea a fost verificată și nu avem user = neautentificat
      if (!user) {
        logger.log("❌ [ACCESS-CHECK] User not authenticated - redirecting to auth");
        navigate('/auth?redirect=/strategic-advisor');
        return;
      }

      try {
        logger.log("🔐 [ACCESS-CHECK] Checking access for user:", user.id, user.email);
        
        // ✅ ADMIN BYPASS: Adminii au acces complet fără verificări
        let isAdmin = false;
        
        try {
          const { data: adminData, error: adminError } = await supabase.rpc('has_role', {
            _user_id: user.id,
            _role: 'admin'
          });
          
          if (adminError) {
            logger.warn("⚠️ [ACCESS-CHECK] has_role RPC error:", adminError.message);
            // Fallback: verifică email pentru admin cunoscut
            if (user.email === 'office@velcont.com') {
              logger.log("✅ [ACCESS-CHECK] Admin fallback by email");
              isAdmin = true;
            }
          } else {
            isAdmin = !!adminData;
          }
        } catch (rpcError) {
          logger.warn("⚠️ [ACCESS-CHECK] RPC exception:", rpcError);
          // Fallback sigur pentru admin
          if (user.email === 'office@velcont.com') {
            logger.log("✅ [ACCESS-CHECK] Admin fallback by email (exception)");
            isAdmin = true;
          }
        }
        
        if (isAdmin) {
          logger.log("✅ [ACCESS-CHECK] Admin user detected - granting full access");
          setIsAdminUser(true);
          setHasAccess(true);
          setCreditRemaining(999);
          setIsCheckingAccess(false);
          return;
        }
        
        const { data: profile, error: profileError } = await supabase
          .from("profiles")
          .select("subscription_status, subscription_type, trial_credit_remaining, stripe_subscription_id, has_free_access")
