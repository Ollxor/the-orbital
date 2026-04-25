/**
 * geo-expand.mjs
 * 1. Split continent:americas → north-america / latin-america (based on subregion)
 * 2. Add 22 new actors from Africa, Asia, Latin America, Oceania, Transnational
 * Run: node scripts/geo-expand.mjs
 */

import { readFileSync, writeFileSync } from 'fs';

const ACTORS_PATH = 'src/data/actors.json';
const actors = JSON.parse(readFileSync(ACTORS_PATH, 'utf8'));

// ── Step 1: Split americas → north-america / latin-america ──────────────────

const NORTH_SUBREGIONS = new Set(['northern-america']);
// central-america, caribbean, south-america → latin-america

let splitCount = 0;
const updated = actors.map(a => {
  if (a.continent !== 'americas') return a;
  const isNorth = NORTH_SUBREGIONS.has(a.subregion);
  splitCount++;
  return { ...a, continent: isNorth ? 'north-america' : 'latin-america' };
});

console.log(`Americas split: ${splitCount} actors updated`);

// ── Step 2: New actors ──────────────────────────────────────────────────────

const newActors = [

  // ── AFRICA ────────────────────────────────────────────────────────────────

  {
    slug: 'african-climate-foundation',
    name: 'African Climate Foundation',
    type: 'Research',
    description: 'An African-led foundation working at the nexus of climate change and developmental justice across the continent.',
    about: 'The African Climate Foundation (ACF) is the first African-led strategic grant-maker and think-do tank working at the nexus of climate change and developmental justice. Founded in 2020 and based in Cape Town, ACF funds African-led solutions to the climate crisis and pushes for ambitious climate policy on the continent. It brings African voices and priorities into global climate governance conversations — particularly around just energy transition, climate finance access, and continental resilience — insisting that African communities must set the terms of their own transition.',
    website: 'https://africanclimatefoundation.org',
    location: 'Cape Town, South Africa',
    scale: 'Continental',
    orientations: ['ASSEMBLY', 'GARDEN'],
    tags: ['climate-policy', 'climate-finance', 'just-transition', 'africa'],
    image: '', imageAlt: '', founded: '2020', lastActive: '', fundingDisclosure: '',
    continent: 'africa', subregion: 'southern-africa', country: ['ZA'], bioregion: [], peoples: [], languages: [],
  },

  {
    slug: 'pan-african-climate-justice-alliance',
    name: 'Pan African Climate Justice Alliance',
    type: 'Network',
    description: 'A consortium of over 2,000 civil society organisations across 54 African countries advancing climate justice from a people-centred, rights-based perspective.',
    about: 'The Pan African Climate Justice Alliance (PACJA) is one of the largest civil society coalitions on the continent, bringing together grassroots groups, faith organisations, farmers, pastoralists, and NGOs around a shared demand for climate justice. Founded in 2008 in Johannesburg, PACJA is the principal African voice in international climate negotiations, insisting that communities least responsible for emissions must not bear the cost of adaptation. Its campaigns press both African governments and wealthy nations on finance, loss and damage, and the right to a just transition.',
    website: 'https://pacja.org',
    location: 'Johannesburg, South Africa / Pan-African',
    scale: 'Continental',
    orientations: ['ASSEMBLY', 'GARDEN'],
    tags: ['climate-justice', 'civil-society', 'africa', 'loss-and-damage'],
    image: '', imageAlt: '', founded: '2008', lastActive: '', fundingDisclosure: '',
    continent: 'africa', subregion: 'southern-africa', country: ['ZA'], bioregion: [], peoples: [], languages: [],
  },

  {
    slug: 'shack-slum-dwellers-international',
    name: 'Shack/Slum Dwellers International',
    type: 'Network',
    description: 'A global network of community-based federations of the urban poor, rooted in self-organising practices developed by slum and shack dwellers across the Global South.',
    about: 'Shack/Slum Dwellers International (SDI) links federations of the urban poor across more than 30 countries in Africa, Asia, and Latin America. Its members — largely women — organise around savings, enumeration of their communities, and negotiation with city governments for land security and basic services. SDI represents a form of democratic governance from below: residents map their own settlements, produce their own data, and negotiate directly with the state. It is one of the most significant models of community-driven urban governance in the world.',
    website: 'https://sdinet.org',
    location: 'Cape Town, South Africa / Global',
    scale: 'Global',
    orientations: ['ASSEMBLY'],
    tags: ['urban-governance', 'housing', 'community-organising', 'global-south'],
    image: '', imageAlt: '', founded: '1996', lastActive: '', fundingDisclosure: '',
    continent: 'africa', subregion: 'southern-africa', country: ['ZA'], bioregion: [], peoples: [], languages: [],
  },

  {
    slug: 'african-biodiversity-network',
    name: 'African Biodiversity Network',
    type: 'Network',
    description: 'A Pan-African network defending seed sovereignty, indigenous food systems, and community rights against industrial agriculture and extractivism.',
    about: 'The African Biodiversity Network (ABN) brings together individuals and organisations across 19 African countries to resist the erosion of agricultural biodiversity and the knowledge systems that sustain it. ABN works on seed sovereignty, opposition to GMOs in African food systems, agroecological alternatives to industrial farming, and the rights of smallholder farmers and pastoralists. It sits at the intersection of ecology and governance: who controls seeds controls food systems, and ABN insists that control belongs with communities, not corporations or states.',
    website: 'https://africanbiodiversity.org',
    location: 'Thika, Kenya / Pan-African',
    scale: 'Continental',
    orientations: ['GARDEN', 'ASSEMBLY'],
    tags: ['seed-sovereignty', 'agroecology', 'food-sovereignty', 'africa', 'indigenous-knowledge'],
    image: '', imageAlt: '', founded: '1999', lastActive: '', fundingDisclosure: '',
    continent: 'africa', subregion: 'eastern-africa', country: ['KE'], bioregion: [], peoples: [], languages: [],
  },

  {
    slug: 'green-belt-movement',
    name: 'Green Belt Movement',
    type: 'NGO',
    description: 'A Kenyan environmental NGO founded by Nobel laureate Wangari Maathai, linking tree planting to democratic culture, women\'s empowerment, and community governance.',
    about: 'Founded by Wangari Maathai in 1977, the Green Belt Movement began as a grassroots response to environmental degradation — asking women to plant trees to restore degraded land. Over decades it became something far larger: a demonstration that ecological health, democratic governance, and women\'s empowerment are inseparable. Maathai won the Nobel Peace Prize in 2004. The movement has planted over 51 million trees and continues to work on reforestation, civic education, and the links between ecological and political freedom — a model that influenced environmental and democratic movements worldwide.',
    website: 'https://greenbeltmovement.org',
    location: 'Nairobi, Kenya',
    scale: 'National',
    orientations: ['GARDEN', 'ASSEMBLY'],
    tags: ['reforestation', 'women', 'civic-culture', 'africa', 'ecological-democracy'],
    image: '', imageAlt: '', founded: '1977', lastActive: '', fundingDisclosure: '',
    continent: 'africa', subregion: 'eastern-africa', country: ['KE'], bioregion: [], peoples: [], languages: [],
  },

  {
    slug: 'great-green-wall-initiative',
    name: 'Great Green Wall Initiative',
    type: 'Government',
    description: 'An African Union-led initiative to restore 100 million hectares of degraded land across the Sahel — an 8,000km mosaic of restored landscapes spanning the full width of Africa.',
    about: 'Launched by the African Union in 2007, the Great Green Wall aims to restore degraded land, fight desertification, and improve food security and climate resilience across 22 countries from Senegal to Djibouti. Its goals include restoring 100 million hectares, sequestering 250 million tons of carbon, and creating 10 million green jobs by 2030. The initiative explicitly links ecological restoration with social stability and is a governance experiment requiring unprecedented coordination across sovereign states around a shared ecosystem. It is also a test of whether global climate finance can actually reach the communities on the frontline of climate disruption.',
    website: 'https://thegreatgreenwall.org',
    location: 'Sahel Region, Africa',
    scale: 'Continental',
    orientations: ['GARDEN', 'ASSEMBLY'],
    tags: ['restoration', 'desertification', 'sahel', 'africa', 'land-use'],
    image: '', imageAlt: '', founded: '2007', lastActive: '', fundingDisclosure: '',
    continent: 'africa', subregion: null, country: [], bioregion: ['Sahel'], peoples: [], languages: [],
  },

  {
    slug: 'iclei-africa',
    name: 'ICLEI Africa',
    type: 'Network',
    description: 'The African regional office of ICLEI – Local Governments for Sustainability, supporting African cities and municipalities in building low-carbon, resilient urban futures.',
    about: 'ICLEI Africa is the regional node of the global ICLEI network for African municipalities and sub-national governments. It works with cities across the continent to embed climate resilience, sustainable urban planning, and low-emission development into local governance. African cities face accelerating urbanisation, climate risk, and severely constrained resources simultaneously — ICLEI Africa builds peer networks, tools, and political will for local governments to act collectively. It connects municipal action to national and international climate governance frameworks, including the UNFCCC and the African Union\'s Agenda 2063.',
    website: 'https://africa.iclei.org',
    location: 'Cape Town, South Africa',
    scale: 'Continental',
    orientations: ['ASSEMBLY', 'SPACESHIP'],
    tags: ['urban-governance', 'cities', 'climate-resilience', 'africa', 'local-government'],
    image: '', imageAlt: '', founded: '1995', lastActive: '', fundingDisclosure: '',
    continent: 'africa', subregion: 'southern-africa', country: ['ZA'], bioregion: [], peoples: [], languages: [],
  },

  // ── ASIA ──────────────────────────────────────────────────────────────────

  {
    slug: 'sewa-india',
    name: 'SEWA — Self Employed Women\'s Association',
    type: 'Movement',
    description: 'One of India\'s largest trade unions, organising millions of informal-sector women workers into cooperative enterprises and a self-built welfare system.',
    about: 'Founded in 1972 in Ahmedabad by Ela Bhatt, SEWA (Self Employed Women\'s Association) is a trade union and cooperative movement representing over 2.5 million informal-sector women workers — street vendors, home-based workers, agricultural labourers, and waste pickers. SEWA has built its own bank, healthcare system, childcare, and social security for workers excluded from formal labour protections. It demonstrates a core principle of the planetary governance movement: governance need not wait for the state. The women of SEWA have collectively constructed welfare institutions, cooperative enterprises, and democratic representation from the ground up.',
    website: 'https://sewa.org',
    location: 'Ahmedabad, India',
    scale: 'National',
    orientations: ['ASSEMBLY'],
    tags: ['labour', 'cooperatives', 'women', 'india', 'informal-economy'],
    image: '', imageAlt: '', founded: '1972', lastActive: '', fundingDisclosure: '',
    continent: 'asia', subregion: 'southern-asia', country: ['IN'], bioregion: [], peoples: [], languages: [],
  },

  {
    slug: 'third-world-network',
    name: 'Third World Network',
    type: 'Network',
    description: 'An international research and advocacy network based in Penang, producing critical analysis of trade, development, and environmental policy from the perspective of the Global South.',
    about: 'Third World Network (TWN) is one of the most influential independent voices in global economic and environmental governance. Founded in 1984 in Penang, it publishes analysis of WTO negotiations, climate agreements, biodiversity policy, and food systems from a perspective explicitly grounded in the rights and interests of developing countries. TWN\'s critical engagement with international institutions has shaped Southern governments\' negotiating positions across decades of multilateral processes — from GATT/WTO to the CBD to the UNFCCC. It remains essential reading for anyone trying to understand why global governance so often fails the people most affected.',
    website: 'https://twn.my',
    location: 'Penang, Malaysia',
    scale: 'Global',
    orientations: ['ASSEMBLY', 'GARDEN'],
    tags: ['trade-policy', 'global-south', 'development', 'multilateralism'],
    image: '', imageAlt: '', founded: '1984', lastActive: '', fundingDisclosure: '',
    continent: 'asia', subregion: 'south-eastern-asia', country: ['MY'], bioregion: [], peoples: [], languages: [],
  },

  {
    slug: 'focus-on-the-global-south',
    name: 'Focus on the Global South',
    type: 'Research',
    description: 'A Bangkok-based policy institute developing alternatives to neoliberal globalisation, centred on the rights, knowledge, and self-determination of Southern peoples.',
    about: 'Founded in 1995 at Chulalongkorn University in Bangkok, Focus on the Global South produces critical research and advocacy on trade, food sovereignty, militarism, and development from a perspective that centres Southern communities and their alternatives. Focus has been a persistent voice in WTO and World Bank negotiations, in anti-war movements, and in debates about food and energy systems. It works across Southeast Asia, South Asia, and the Pacific, and is particularly strong on the political economy of post-growth and commons-based development alternatives.',
    website: 'https://focusweb.org',
    location: 'Bangkok, Thailand',
    scale: 'Global',
    orientations: ['ASSEMBLY', 'GARDEN'],
    tags: ['development-alternatives', 'food-sovereignty', 'global-south', 'political-economy'],
    image: '', imageAlt: '', founded: '1995', lastActive: '', fundingDisclosure: '',
    continent: 'asia', subregion: 'south-eastern-asia', country: ['TH'], bioregion: [], peoples: [], languages: [],
  },

  {
    slug: 'icsf',
    name: 'ICSF — International Collective in Support of Fishworkers',
    type: 'Network',
    description: 'An international network defending the rights and livelihoods of small-scale fishing communities and ocean commons against industrial enclosure.',
    about: 'The International Collective in Support of Fishworkers (ICSF) was founded in 1986 and is based in Chennai, India. It works on the governance of fisheries as a global commons: the rights of small-scale fishing communities, equitable access to coastal and ocean resources, and the threats posed by industrial fishing and aquaculture expansion. ICSF produces policy analysis, supports community advocacy, and connects fishing communities across Asia, Africa, and Latin America with international governance processes — including the FAO\'s Small-Scale Fisheries Guidelines, which ICSF helped shape over many years of engagement.',
    website: 'https://icsf.net',
    location: 'Chennai, India',
    scale: 'Global',
    orientations: ['GARDEN', 'ASSEMBLY'],
    tags: ['fisheries', 'ocean-commons', 'coastal-communities', 'food-sovereignty'],
    image: '', imageAlt: '', founded: '1986', lastActive: '', fundingDisclosure: '',
    continent: 'asia', subregion: 'southern-asia', country: ['IN'], bioregion: [], peoples: [], languages: [],
  },

  {
    slug: 'ibon-international',
    name: 'IBON International',
    type: 'Research',
    description: 'A Philippines-based development organisation building civil society capacity to advance sustainable development and challenge extractive globalisation in international governance.',
    about: 'IBON International is the international arm of IBON Foundation, established in the Philippines in 1978 as a research and education organisation serving progressive civil society. It holds UN ECOSOC consultative status and works with civil society coalitions worldwide on development assistance, public finance, climate finance, and alternatives to neoliberal globalisation. IBON is particularly active in building Southern civil society capacity to engage in international processes where the voice of poor and marginalised communities is structurally underrepresented — including the UN climate process, the Global South civil society engagement with the OECD, and debates about technology transfer.',
    website: 'https://iboninternational.org',
    location: 'Manila, Philippines',
    scale: 'Global',
    orientations: ['ASSEMBLY'],
    tags: ['development-finance', 'global-south', 'civil-society', 'philippines'],
    image: '', imageAlt: '', founded: '1978', lastActive: '', fundingDisclosure: '',
    continent: 'asia', subregion: 'south-eastern-asia', country: ['PH'], bioregion: [], peoples: [], languages: [],
  },

  {
    slug: 'satoyama-initiative',
    name: 'Satoyama Initiative (IPSI)',
    type: 'Network',
    description: 'A UNU-led global partnership of nearly 300 organisations working on the governance and stewardship of socio-ecological production landscapes and seascapes.',
    about: 'The International Partnership for the Satoyama Initiative (IPSI) is co-organised by the UN University Institute for the Advanced Study of Sustainability (UNU-IAS) and the CBD Secretariat. It draws on the Japanese concept of satoyama — the human-managed landscape between wilderness and cultivation — to describe a broader global category: production landscapes jointly shaped by ecological processes and local cultural practice. IPSI brings together nearly 300 organisations to study, restore, and govern these landscapes, which range from traditional agroforestry systems to coastal fishing commons. It connects landscape-level practice with biodiversity governance at the CBD, grounding global policy in local knowledge.',
    website: 'https://satoyamainitiative.org',
    location: 'Tokyo, Japan / Global',
    scale: 'Global',
    orientations: ['GARDEN', 'ASSEMBLY'],
    tags: ['landscape-governance', 'biodiversity', 'agroecology', 'traditional-knowledge', 'commons'],
    image: '', imageAlt: '', founded: '2010', lastActive: '', fundingDisclosure: '',
    continent: 'asia', subregion: 'eastern-asia', country: ['JP'], bioregion: [], peoples: [], languages: [],
  },

  // ── LATIN AMERICA ─────────────────────────────────────────────────────────

  {
    slug: 'fundacion-avina',
    name: 'Fundación Avina',
    type: 'Network',
    description: 'A Latin American philanthropic foundation building alliances between civil society, business, and government around democratic innovation, climate action, and just economies.',
    about: 'Fundación Avina was founded in 1994 and is headquartered in Panama, with offices across Latin America. Over 30 years it has developed a distinctive collaborative model — brokering alliances, co-investing in shared strategies, and supporting social entrepreneurs to scale. Its current focus areas are democratic innovation, climate action, and just and regenerative economy. Avina is particularly strong on the collaborative infrastructure of systemic change: how do actors across sectors actually align around transformative goals? Its experience in Latin America makes it a key practitioner of multi-stakeholder governance at continental scale.',
    website: 'https://avina.net',
    location: 'Panama City, Panama / Latin America',
    scale: 'Continental',
    orientations: ['ASSEMBLY', 'GARDEN'],
    tags: ['philanthropy', 'latin-america', 'democratic-innovation', 'climate-action'],
    image: '', imageAlt: '', founded: '1994', lastActive: '', fundingDisclosure: '',
    continent: 'latin-america', subregion: 'central-america', country: ['PA'], bioregion: [], peoples: [], languages: [],
  },

  {
    slug: 'coica',
    name: 'COICA — Coordinator of Indigenous Organizations of the Amazon Basin',
    type: 'Network',
    description: 'The coordinating body of nine national Indigenous organisations representing peoples across the nine Amazonian countries in international governance and territorial defence.',
    about: 'COICA (Coordinadora de las Organizaciones Indígenas de la Cuenca Amazónica) was founded in Lima in 1984 and is based in Quito. It represents the Indigenous federations of nine Amazonian nations in international governance processes. COICA has been central to establishing that Indigenous territorial rights are the most effective mechanism for Amazon conservation — a scientific and political argument the organisation has pressed for four decades. It advocates for free, prior and informed consent; legal recognition of ancestral territories; and protection of peoples living in voluntary isolation. As the Amazon approaches ecological tipping points, COICA\'s governance model becomes increasingly urgent.',
    website: 'https://coicamazonia.org',
    location: 'Quito, Ecuador',
    scale: 'Continental',
    orientations: ['GARDEN', 'ASSEMBLY'],
    tags: ['indigenous-rights', 'amazon', 'territorial-rights', 'fpic', 'latin-america'],
    image: '', imageAlt: '', founded: '1984', lastActive: '', fundingDisclosure: '',
    continent: 'latin-america', subregion: 'south-america', country: ['EC'], bioregion: ['Amazonia'], peoples: [], languages: [],
  },

  {
    slug: 'ipam-amazonia',
    name: 'IPAM Amazônia',
    type: 'Research',
    description: 'A Brazilian non-profit research and policy institute working on climate science, deforestation, and the governance of the Amazon and Cerrado biomes.',
    about: 'Founded in 1995 in Belém, the Amazon Environmental Research Institute (IPAM) is one of Brazil\'s most significant independent research institutions for Amazonian science and policy. It produces scientific knowledge on deforestation, carbon stocks, fire, and land-use change, and translates that knowledge into policy engagement. IPAM works on three axes: low-carbon farming, protected territory governance, and sustainable family production. It makes the scientific and economic case that Amazon protection is compatible with — and necessary for — sustainable development, directly challenging the political economy of deforestation in Brazil.',
    website: 'https://ipam.org.br',
    location: 'Brasília, Brazil',
    scale: 'National',
    orientations: ['GARDEN', 'SPACESHIP'],
    tags: ['amazon', 'deforestation', 'climate-science', 'brazil', 'land-use'],
    image: '', imageAlt: '', founded: '1995', lastActive: '', fundingDisclosure: '',
    continent: 'latin-america', subregion: 'south-america', country: ['BR'], bioregion: ['Amazonia'], peoples: [], languages: [],
  },

  {
    slug: 'mst-brazil',
    name: 'MST — Movimento dos Trabalhadores Rurais Sem Terra',
    type: 'Movement',
    description: 'Brazil\'s Landless Workers\' Movement — one of the largest social movements in the world, organising landless rural families to occupy unused land, build agroecological settlements, and practise food sovereignty.',
    about: 'The MST (Landless Workers\' Movement) was formally founded in 1984 and has grown into one of the world\'s largest social movements, with hundreds of thousands of families in organised settlements. MST occupies large landholdings not fulfilling their social function under Brazilian law, negotiates land reform, and builds collective communities practising agroecology and food sovereignty. Settlements run their own schools, health systems, and cooperative enterprises — making MST one of the most ambitious experiments in democratic self-governance in the contemporary world. It is a central actor in the global food sovereignty movement and La Via Campesina.',
    website: 'https://mst.org.br',
    location: 'São Paulo, Brazil',
    scale: 'National',
    orientations: ['GARDEN', 'ASSEMBLY'],
    tags: ['land-reform', 'food-sovereignty', 'agroecology', 'brazil', 'cooperative'],
    image: '', imageAlt: '', founded: '1984', lastActive: '', fundingDisclosure: '',
    continent: 'latin-america', subregion: 'south-america', country: ['BR'], bioregion: [], peoples: [], languages: [],
  },

  {
    slug: 'filac',
    name: 'FILAC — Fund for the Development of Indigenous Peoples of Latin America',
    type: 'Government',
    description: 'An intergovernmental body where Indigenous peoples and governments share equal decision-making power, working to advance indigenous self-development across Latin America and the Caribbean.',
    about: 'FILAC (Fondo para el Desarrollo de los Pueblos Indígenas de América Latina y el Caribe) was created by the Second Ibero-American Summit in 1992 with a governance structure that gives Indigenous peoples and governments equal representation — a rare model of shared sovereignty. It supports Indigenous self-development processes, promotes Buen Vivir / Vivir Bien as an alternative development framework, and works on indigenous languages, gender equality, and territorial rights. FILAC holds Permanent Observer status at the UN General Assembly. Its structure — co-governed by states and peoples on equal terms — embodies precisely the kind of plurinational governance design that planetary governance ultimately requires.',
    website: 'https://filac.org',
    location: 'La Paz, Bolivia',
    scale: 'Continental',
    orientations: ['ASSEMBLY', 'GARDEN'],
    tags: ['indigenous-rights', 'buen-vivir', 'latin-america', 'self-determination', 'governance'],
    image: '', imageAlt: '', founded: '1992', lastActive: '', fundingDisclosure: '',
    continent: 'latin-america', subregion: 'south-america', country: ['BO'], bioregion: [], peoples: [], languages: [],
  },

  // ── OCEANIA ───────────────────────────────────────────────────────────────

  {
    slug: 'pican',
    name: 'PICAN — Pacific Islands Climate Action Network',
    type: 'Network',
    description: 'The regional civil society alliance of Pacific Island organisations advocating for climate justice and ambitious global action in international negotiations.',
    about: 'The Pacific Islands Climate Action Network (PICAN) brings together over 190 civil society organisations across Pacific Island countries to amplify the Pacific voice in global climate governance. Established in 2013 and part of Climate Action Network International, PICAN coordinates national civil society nodes across Fiji, Samoa, Vanuatu, and beyond. The Pacific Islands are among the most vulnerable places on Earth to sea-level rise and climate disruption — PICAN turns that frontline experience into political advocacy, demanding loss and damage finance, rapid global decarbonisation, and recognition of climate-driven human rights. The movement\'s moral authority in climate negotiations is unmatched.',
    website: 'https://pican.org',
    location: 'Suva, Fiji / Pacific Region',
    scale: 'Regional',
    orientations: ['ASSEMBLY', 'GARDEN'],
    tags: ['climate-justice', 'pacific', 'sea-level-rise', 'loss-and-damage', 'small-island-states'],
    image: '', imageAlt: '', founded: '2013', lastActive: '', fundingDisclosure: '',
    continent: 'oceania', subregion: 'melanesia', country: ['FJ'], bioregion: ['Pacific Islands'], peoples: [], languages: [],
  },

  {
    slug: 'pacific-community-spc',
    name: 'Pacific Community (SPC)',
    type: 'Government',
    description: 'The principal intergovernmental scientific and technical organisation supporting development across the Pacific, providing data, analysis, and policy capacity to 26 Pacific nations and territories.',
    about: 'The Pacific Community (SPC) was founded in 1947 and is the oldest and most comprehensive intergovernmental organisation in the Pacific. Based in Noumea, it serves 26 Pacific Island countries and territories with scientific and technical expertise across fisheries, public health, geoscience, social development, and ocean governance. SPC manages key Pacific data commons and supports member nations\' capacity to participate in international governance processes. For small island states with limited institutional capacity, SPC is often the primary source of technical knowledge needed to govern complex ocean and climate systems. It is the backbone infrastructure of Pacific collective governance.',
    website: 'https://spc.int',
    location: 'Noumea, New Caledonia / Pacific Region',
    scale: 'Regional',
    orientations: ['ASSEMBLY', 'SPACESHIP'],
    tags: ['pacific', 'fisheries', 'ocean-governance', 'data', 'small-island-states'],
    image: '', imageAlt: '', founded: '1947', lastActive: '', fundingDisclosure: '',
    continent: 'oceania', subregion: 'melanesia', country: ['NC'], bioregion: ['Pacific Islands'], peoples: [], languages: [],
  },

  {
    slug: 'sprep',
    name: 'SPREP — Secretariat of the Pacific Regional Environment Programme',
    type: 'Government',
    description: 'The intergovernmental body responsible for protecting and managing the environment and natural resources of the Pacific region on behalf of 26 member nations and territories.',
    about: 'SPREP (Secretariat of the Pacific Regional Environment Programme) was established in 1982 and is based in Apia, Samoa. It serves 26 member nations across climate change adaptation, biodiversity conservation, waste management, and ocean governance. SPREP coordinates the Pacific\'s engagement with major multilateral environmental agreements including the UNFCCC, CBD, and Basel Convention. For a region of extraordinary ecological diversity and fragility — including some of the world\'s most important ocean and reef ecosystems — SPREP represents the governance infrastructure through which Pacific peoples protect their shared natural inheritance.',
    website: 'https://sprep.org',
    location: 'Apia, Samoa',
    scale: 'Regional',
    orientations: ['GARDEN', 'ASSEMBLY'],
    tags: ['pacific', 'biodiversity', 'ocean', 'climate-adaptation', 'small-island-states'],
    image: '', imageAlt: '', founded: '1982', lastActive: '', fundingDisclosure: '',
    continent: 'oceania', subregion: 'polynesia', country: ['WS'], bioregion: ['Pacific Islands'], peoples: [], languages: [],
  },

  // ── TRANSNATIONAL ─────────────────────────────────────────────────────────

  {
    slug: 'la-via-campesina',
    name: 'La Via Campesina',
    type: 'Movement',
    description: 'The international peasant movement — a global alliance of small farmers, landless workers, indigenous peoples, and rural women that coined the concept of food sovereignty.',
    about: 'La Via Campesina represents an estimated 200 million farmers, landless workers, rural women, and indigenous peoples across 81 countries. Founded in 1993, it coined the concept of food sovereignty — the right of peoples to define their own food and agriculture systems — which has become a foundational principle in international food politics. La Via Campesina campaigns against industrial agriculture, land grabbing, free trade agreements, and GMOs, while promoting agroecology, seed sovereignty, and land reform. It is one of the most significant examples in existence of transnational democratic governance: millions of people across the world coordinating around shared principles without a state.',
    website: 'https://viacampesina.org',
    location: 'Harare, Zimbabwe / Global',
    scale: 'Global',
    orientations: ['GARDEN', 'ASSEMBLY'],
    tags: ['food-sovereignty', 'peasant-rights', 'agroecology', 'land-reform', 'seed-sovereignty'],
    image: '', imageAlt: '', founded: '1993', lastActive: '', fundingDisclosure: '',
    continent: 'transnational', subregion: null, country: ['ZW'], bioregion: [], peoples: [], languages: [],
  },

];

// Check for slug collisions
const existingSlugs = new Set(updated.map(a => a.slug));
const collisions = newActors.filter(a => existingSlugs.has(a.slug));
if (collisions.length) {
  console.error('SLUG COLLISIONS:', collisions.map(a => a.slug));
  process.exit(1);
}

const final = [...updated, ...newActors];

writeFileSync(ACTORS_PATH, JSON.stringify(final, null, 2) + '\n', 'utf8');

// Verify UTF-8 cleanliness
const raw = readFileSync(ACTORS_PATH, 'utf8');
const mojibake = (raw.match(/â€|Ã¤|Ã¶|Ã¼|Ã©/g) || []).length;
console.log(`Mojibake check: ${mojibake === 0 ? '0 — clean' : mojibake + ' INSTANCES FOUND!'}`);
console.log(`Total actors: ${final.length} (was ${actors.length}, added ${newActors.length})`);

// Continent distribution
const cc = {};
final.forEach(a => { cc[a.continent] = (cc[a.continent]||0)+1; });
console.log('\nContinent distribution:');
Object.entries(cc).sort((a,b)=>b[1]-a[1]).forEach(([k,v])=>console.log(' ', v, k));
