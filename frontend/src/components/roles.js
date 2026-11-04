// The three roles in the database (users.role).
// ASSUMPTION: confirm the exact enum values with whoever owns the schema.
export const ROLE = {
  END_USER: 'END_USER',
  SECURITY_AUDITOR: 'SECURITY_AUDITOR',
  CLIENT_ADMIN: 'CLIENT_ADMIN',
};

export const PRIVILEGED_ROLES = [ROLE.SECURITY_AUDITOR, ROLE.CLIENT_ADMIN];

// Employees never see the technical role names. They pick a job title, and each
// title sits under a plain-language group that maps to exactly one database role.
export const ROLE_GROUPS = [
  {
    role: ROLE.END_USER,
    title: 'Use the AI assistant',
    description: 'Ask the AI questions and manage your documents.',
    access: [
      'Ask the AI questions and see which answers are verified',
      'Upload your documents and check them before they are used',
    ],
    positions: [
      'Customer Support Agent',
      'Sales Representative',
      'Marketing Specialist',
      'HR Specialist',
      'Finance / Accounting Specialist',
      'Operations Coordinator',
      'Product / Project Manager',
      'Other team member',
    ],
  },
  {
    role: ROLE.SECURITY_AUDITOR,
    title: 'Test and audit the AI',
    description: 'Find weaknesses and review security and compliance results.',
    access: [
      'Review security threats found in the AI',
      'Export compliance and audit reports',
      'See the system health overview',
    ],
    positions: [
      'CISO / Head of Security',
      'Information Security Analyst',
      'Penetration Tester',
      'Compliance Officer',
      'Risk Manager',
      'Internal Auditor',
      'Legal Counsel / Data Protection Officer',
      'QA Engineer',
    ],
  },
  {
    role: ROLE.CLIENT_ADMIN,
    title: 'Manage the platform',
    description: 'Oversee the whole platform for your company.',
    access: [
      'Access to every page: overview, evaluation, threats, knowledge base and compliance',
    ],
    positions: [
      'CEO / Founder / General Manager',
      'CTO / VP Engineering',
      'IT Manager / Administrator',
      'Engineering Manager',
      'DevOps / Platform Engineer',
      'AI / ML Engineer',
    ],
  },
];

// Which dashboard pages each role may open, and where it lands after login.
export const ROLE_ACCESS = {
  [ROLE.END_USER]: { pages: ['evaluate', 'knowledge-base'], home: 'evaluate' },
  [ROLE.SECURITY_AUDITOR]: { pages: ['overview', 'threats', 'compliance'], home: 'overview' },
  [ROLE.CLIENT_ADMIN]: {
    pages: ['overview', 'evaluate', 'threats', 'knowledge-base', 'compliance'],
    home: 'overview',
  },
};

const POSITION_TO_ROLE = Object.fromEntries(
  ROLE_GROUPS.flatMap((group) => group.positions.map((position) => [position, group.role]))
);

export const roleForPosition = (position) => POSITION_TO_ROLE[position] ?? null;
export const groupForRole = (role) => ROLE_GROUPS.find((g) => g.role === role) ?? null;
export const canAccess = (role, pageId) => ROLE_ACCESS[role]?.pages.includes(pageId) ?? false;
export const homeFor = (role) => ROLE_ACCESS[role]?.home ?? 'evaluate';
