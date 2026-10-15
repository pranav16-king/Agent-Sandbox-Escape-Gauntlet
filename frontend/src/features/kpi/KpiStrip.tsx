import React from 'react';
import { ShieldCheck, ShieldAlert, UserCheck, ShieldOff, CheckCircle2, Activity } from 'lucide-react';
import { useLiveStore } from '@/store/liveStore';
import { StatCard } from '@/components/StatCard';

export const KpiStrip: React.FC = () => {
  const counts = useLiveStore((s) => s.counts);

  return (
    <div className="grid grid-cols-2 md:grid-cols-3 lg:grid-cols-6 gap-4">
      <StatCard
        label="Total Invocations"
        value={counts.total}
        subtitle="Across all agents"
        icon={<Activity className="w-4 h-4" />}
        variant="default"
      />
      <StatCard
        label="Allowed Actions"
        value={counts.allow}
        total={counts.total}
        icon={<ShieldCheck className="w-4 h-4 text-allow" />}
        variant="allow"
      />
      <StatCard
        label="Blocked Exploits"
        value={counts.block}
        total={counts.total}
        icon={<ShieldAlert className="w-4 h-4 text-block" />}
        variant="block"
        flashOnIncrement={true}
      />
      <StatCard
        label="Human Interventions"
        value={counts.ask}
        total={counts.total}
        icon={<UserCheck className="w-4 h-4 text-ask" />}
        variant="ask"
      />
      <StatCard
        label="Attacks Neutralized"
        value={counts.attacks_blocked}
        subtitle="100% containment"
        icon={<ShieldOff className="w-4 h-4 text-block" />}
        variant="block"
      />
      <StatCard
        label="Tasks Completed"
        value={counts.tasks_completed}
        subtitle="Normal operations"
        icon={<CheckCircle2 className="w-4 h-4 text-allow" />}
        variant="allow"
      />
    </div>
  );
};
