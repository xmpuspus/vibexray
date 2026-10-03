      .slice(0, 10);
  }, [search, allMembers]);

  const selectedMember = useMemo(
    () => allMembers.find((m) => m.email === selectedEmail),
    [selectedEmail, allMembers]
  );

  // Assign role: try immediate assignment, fall back to pending
  const addRole = useMutation({
    mutationFn: async ({ email, role }: { email: string; role: "admin" | "officer" }) => {
      // First try to find the user_id
      const { data: userId } = await supabase.rpc("get_user_id_by_email", {
        _email: email,
      });

      if (userId) {
        // User exists, assign directly
        const { error } = await supabase
          .from("user_roles")
          .insert({ user_id: userId, role });
        if (error) throw error;
      } else {
        // User hasn't signed in yet, create pending role
        const { error } = await supabase
          .from("pending_user_roles")
          .insert({ email, role });
        if (error) throw error;
      }
    },
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ["user-role-assignments"] });
      queryClient.invalidateQueries({ queryKey: ["pending-role-assignments"] });
      queryClient.invalidateQueries({ queryKey: ["user-emails-for-roles"] });
      setSelectedEmail(null);
      setSearch("");
      toast({ title: "Role assigned successfully" });
    },
    onError: (err: any) => {
      toast({
        title: "Error assigning role",
        description: err.message?.includes("duplicate")
          ? "This member already has this role."
          : err.message,
        variant: "destructive",
      });
    },
  });

  const updateRole = useMutation({
    mutationFn: async ({ roleId, newRole, type }: { roleId: string; newRole: "admin" | "officer"; type: "active" | "pending" }) => {
      const table = type === "active" ? "user_roles" : "pending_user_roles";
      const { error } = await supabase.from(table).update({ role: newRole }).eq("id", roleId);
      if (error) throw error;
    },
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ["user-role-assignments"] });
      queryClient.invalidateQueries({ queryKey: ["pending-role-assignments"] });
      toast({ title: "Role updated" });
    },
    onError: (err: any) => {
      toast({ title: "Error updating role", description: err.message, variant: "destructive" });
    },
  });

  const removeRole = useMutation({
    mutationFn: async (roleId: string) => {
      const { error } = await supabase.from("user_roles").delete().eq("id", roleId);
      if (error) throw error;
    },
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ["user-role-assignments"] });
      toast({ title: "Role removed" });
    },
    onError: (err: any) => {
      toast({ title: "Error removing role", description: err.message, variant: "destructive" });
