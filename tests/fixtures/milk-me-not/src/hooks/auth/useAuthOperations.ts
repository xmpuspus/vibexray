      toast({
        title: "Too many attempts",
        description: `Please wait ${retryMinutes} minute${retryMinutes !== 1 ? 's' : ''} before trying again.`,
        variant: "destructive"
      });
      setLoading(false);
      return { success: false };
    }
    try {
      const { error } = await supabase.auth.signInWithPassword({
        email: sanitizedEmail,
        password,
      });
      
      if (error) {
        // Log failed login attempt for security monitoring
        await logSecurityEvent('login_failed', { 
          email: sanitizedEmail, 
          error: error.message 
        });

        if (error.message.includes('Invalid login credentials')) {
          toast({
            title: "Invalid credentials",
            description: "Please check your email and password and try again.",
            variant: "destructive",
          });
        } else {
          toast({
            title: "Login Failed",
            description: "Something went wrong. Please try again.",
            variant: "destructive",
          });
        }
        return { success: false };
      }

      await refreshAuth();
      return { success: true };
    } catch (error: any) {
      toast({
        title: "Error",
        description: error.message,
        variant: "destructive",
      });
      return { success: false };
    } finally {
      setLoading(false);
    }
  };

  const signUp = async ({ email, password, username }: AuthFormData) => {
    const sanitizedEmail = sanitizeInput(email).toLowerCase();
    const sanitizedUsername = sanitizeInput(username);
    const rateLimitKey = `signup_${sanitizedEmail}`;
    
    if (!signupRateLimit.canAttempt(rateLimitKey)) {
      const remainingTime = Math.ceil(signupRateLimit.getRemainingTime(rateLimitKey) / 60000);
      toast({
        title: "Too many attempts",
        description: `Please wait ${remainingTime} minutes before trying again.`,
