import React from 'react';
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from '@/components/ui/card';
import { Tabs, TabsContent, TabsList, TabsTrigger } from '@/components/ui/tabs';
import { FamilyAgentIntegration } from '@/components/admin/FamilyAgentIntegration';
import { PatronDashboard } from '@/components/admin/PatronDashboard';
import { DivisionLeadersPanel } from '@/components/admin/DivisionLeadersPanel';
import { ContactManagement } from '@/components/admin/ContactManagement';
import { ContactAnalytics } from '@/components/analytics/ContactAnalytics';
import { Footer } from '@/components/ui/footer';
import { Database, Users, Settings, BarChart3, Crown, Building2, Mail, TestTube } from 'lucide-react';

const Admin = () => {
  return (
    <div className="min-h-screen bg-gradient-to-br from-slate-50 via-blue-50 to-indigo-100 flex flex-col">
      <div className="container mx-auto p-6 space-y-6 flex-grow">
        <div className="space-y-2">
          <h1 className="text-3xl font-bold">Admin Dashboard</h1>
          <p className="text-muted-foreground">
            Manage system configuration, data integration, and consciousness pyramid
          </p>
        </div>

        <Tabs defaultValue="patron" className="space-y-4">
          <TabsList>
            <TabsTrigger value="patron" className="flex items-center gap-2">
              <Crown className="h-4 w-4" />
              Patron
            </TabsTrigger>
            <TabsTrigger value="divisions" className="flex items-center gap-2">
              <Building2 className="h-4 w-4" />
              Division Leaders
            </TabsTrigger>
            <TabsTrigger value="integration" className="flex items-center gap-2">
              <Users className="h-4 w-4" />
              Agent Integration
            </TabsTrigger>
            <TabsTrigger value="contacts" className="flex items-center gap-2">
              <Mail className="h-4 w-4" />
              Contacts
            </TabsTrigger>
            <TabsTrigger value="analytics" className="flex items-center gap-2">
              <BarChart3 className="h-4 w-4" />
              Contact Analytics
            </TabsTrigger>
            <TabsTrigger value="database" className="flex items-center gap-2">
              <Database className="h-4 w-4" />
              Database
            </TabsTrigger>
            <TabsTrigger value="settings" className="flex items-center gap-2">
              <Settings className="h-4 w-4" />
              Settings
            </TabsTrigger>
          </TabsList>

          <TabsContent value="patron" className="space-y-4">
            <PatronDashboard />
          </TabsContent>

          <TabsContent value="divisions" className="space-y-4">
            <DivisionLeadersPanel />
          </TabsContent>

          <TabsContent value="integration" className="space-y-4">
            <FamilyAgentIntegration />
          </TabsContent>

          <TabsContent value="contacts" className="space-y-4">
            <ContactManagement />
          </TabsContent>

          <TabsContent value="analytics" className="space-y-4">
            <ContactAnalytics />
          </TabsContent>

          <TabsContent value="database" className="space-y-4">
            <Card>
              <CardHeader>
                <CardTitle>Database Management</CardTitle>
                <CardDescription>
                  Monitor and manage database operations
                </CardDescription>
              </CardHeader>
              <CardContent>
                <div className="space-y-4">
                  <p className="text-muted-foreground">Database management tools coming soon...</p>
                  <div className="p-4 bg-blue-50 rounded-lg">
                    <h4 className="font-semibold text-blue-800 mb-2">🧪 Contact System Testing</h4>
                    <p className="text-blue-700 text-sm mb-3">
                      Test the complete contact form functionality including email delivery and database storage.
                    </p>
                    <a 
                      href="/contact-test" 
                      className="inline-flex items-center gap-2 px-3 py-2 bg-blue-600 text-white rounded-md hover:bg-blue-700 transition-colors"
                    >
                      <TestTube className="h-4 w-4" />
                      Open Contact Test Suite
                    </a>
                  </div>
                </div>
              </CardContent>
            </Card>
          </TabsContent>

          <TabsContent value="settings" className="space-y-4">
            <Card>
              <CardHeader>
                <CardTitle>System Settings</CardTitle>
                <CardDescription>
                  Configure system-wide settings and preferences
                </CardDescription>
              </CardHeader>
              <CardContent>
                <p className="text-muted-foreground">Settings panel coming soon...</p>
              </CardContent>
            </Card>
          </TabsContent>
        </Tabs>
      </div>
      <Footer />
    </div>
  );
};

export default Admin;
