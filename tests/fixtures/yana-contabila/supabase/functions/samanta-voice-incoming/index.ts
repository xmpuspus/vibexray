
      const currentTranscript = Array.isArray(call.transcript) ? call.transcript : [];
      const userEntry = { role: "caller", text: speech || "[tăcere]", at: new Date().toISOString() };
      if (!speech) {
        await supabase.from("samanta_calls").update({ transcript: [...currentTranscript, userEntry] }).eq("id", callId);
        return gatherTwiml("Nu v-am auzit clar. Îmi puteți spune, vă rog, cu ce vă ajut?", callId);
      }

      const userName = settings.user_full_name || "Nicolae";
      const company = settings.company_name || "Velcont";
      const systemPrompt = `Ești Samanta, recepționera și asistenta executivă a lui ${userName} de la ${company}. Vorbești exclusiv în română, calm, natural și profesionist. ${company} este un cabinet de contabilitate: contabilitate lunară, consultanță fiscală generală, salarizare, declarații fiscale, suport pentru antreprenori și firme. Preiei mesajul, identifici cine sună și ce dorește. Nu dai sfaturi fiscale concrete și nu promiți termene/prețuri exacte; spui că transmiți mesajul și revine cineva.`;
      const reply = await generateSamantaReply(systemPrompt, speech, currentTranscript);
      const assistantEntry = { role: "samanta", text: reply, at: new Date().toISOString() };
      await supabase
        .from("samanta_calls")
        .update({ transcript: [...currentTranscript, userEntry, assistantEntry] })
        .eq("id", callId);

      return gatherTwiml(reply, callId);
    }

