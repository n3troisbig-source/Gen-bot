require('dotenv').config();
const { Client, GatewayIntentBits, EmbedBuilder, SlashCommandBuilder, REST, Routes, PermissionFlagsBits, ActionRowBuilder, ButtonBuilder, ButtonStyle } = require('discord.js');
const fs = require('fs');
const path = require('path');

// ============================================================
//  CONFIG
// ============================================================
const OWNER_ID = '1455187536623304734';
const DATA_DIR = path.join(__dirname, 'data');
const ACCOUNTS_FILE = path.join(DATA_DIR, 'accounts.json');
const PREMIUM_FILE  = path.join(DATA_DIR, 'premium.json');

if (!fs.existsSync(DATA_DIR)) fs.mkdirSync(DATA_DIR, { recursive: true });

// ---- helpers ------------------------------------------------
function loadJSON(file, def) {
  try { return JSON.parse(fs.readFileSync(file, 'utf8')); }
  catch { return def; }
}
function saveJSON(file, data) {
  fs.writeFileSync(file, JSON.stringify(data, null, 2));
}

function getAccounts() { return loadJSON(ACCOUNTS_FILE, []); }
function saveAccounts(a) { saveJSON(ACCOUNTS_FILE, a); }
function getPremium()  { return loadJSON(PREMIUM_FILE,  []); }
function savePremium(p) { saveJSON(PREMIUM_FILE, p); }

// ---- parse account line ------------------------------------
function parseAccount(line) {
  // Expected format (flexible):
  // email:password | field | field | ...
  const parts = line.split('|').map(s => s.trim());
  const [email, password] = (parts[0] || '').split(':').map(s => s.trim());
  const obj = { raw: line, email: email || '', password: password || '' };

  for (const part of parts.slice(1)) {
    const lower = part.toLowerCase();
    if (lower.startsWith('verified')) obj.verified = part.split(':').slice(1).join(':').trim();
    else if (lower.startsWith('2fa'))     obj.twoFA   = part.split(':').slice(1).join(':').trim();
    else if (lower.startsWith('banned'))  obj.banned  = part.split(':').slice(1).join(':').trim();
    else if (lower.startsWith('username'))obj.username= part.split(':').slice(1).join(':').trim();
    else if (lower.startsWith('level'))   obj.level   = part.split(':').slice(1).join(':').trim();
    else if (lower.startsWith('platform'))obj.platforms=part.split(':').slice(1).join(':').trim();
    else if (lower.startsWith('credits')) obj.credits = part.split(':').slice(1).join(':').trim();
    else if (lower.startsWith('renown'))  obj.renown  = part.split(':').slice(1).join(':').trim();
    else if (lower.startsWith('items'))   obj.items   = part.split(':').slice(1).join(':').trim();
    else if (lower.startsWith('found ranks') || lower.startsWith('ranks')) obj.ranks = part.split(':').slice(1).join(':').trim();
  }
  return obj;
}

// ---- build DM embed ----------------------------------------
function buildDMEmbed(acc, remaining, user) {
  const embed = new EmbedBuilder()
    .setColor(0xFFD700)
    .setTitle('✨ Premium Account Generated')
    .setThumbnail('https://i.imgur.com/QfkNmWq.png') // R6 icon
    .addFields(
      { name: '📧 Account Details', value: `**Account:** \`\`${acc.email}:${acc.password}\`\`` },
    );

  if (acc.verified)  embed.addFields({ name: '✅ Verified Email/Phone', value: acc.verified,  inline: true });
  if (acc.twoFA)     embed.addFields({ name: '🔐 2FA',                  value: acc.twoFA,     inline: true });
  if (acc.banned)    embed.addFields({ name: '🚫 Banned',               value: acc.banned,    inline: true });
  if (acc.username)  embed.addFields({ name: '👤 Username',             value: acc.username,  inline: true });
  if (acc.level)     embed.addFields({ name: '🎮 Level',                value: acc.level,     inline: true });
  if (acc.platforms) embed.addFields({ name: '🕹️ Platforms',            value: acc.platforms, inline: true });
  if (acc.credits)   embed.addFields({ name: '💰 Credits',              value: acc.credits,   inline: true });
  if (acc.renown)    embed.addFields({ name: '🏅 Renown',               value: acc.renown,    inline: true });
  if (acc.items)     embed.addFields({ name: '🎒 Items',                value: acc.items,     inline: true });
  if (acc.ranks)     embed.addFields({ name: '🏆 Found Ranks',          value: acc.ranks,     inline: false });

  embed.addFields(
    { name: 'Type',                    value: 'Premium Account',  inline: true },
    { name: 'Remaining Premium Stock', value: `${remaining}`,     inline: true },
  )
  .setFooter({ text: 'R6 Generator • Keep this account safe!', iconURL: user.displayAvatarURL() })
  .setTimestamp();

  return embed;
}

// ---- build channel reply embed -----------------------------
function buildChannelEmbed(user, remaining) {
  return new EmbedBuilder()
    .setColor(0x00FF88)
    .setTitle('✨ Premium Account Generated')
    .setThumbnail(user.displayAvatarURL({ dynamic: true }))
    .addFields(
      { name: 'User',    value: `<@${user.id}>`,       inline: true },
      { name: 'Type',    value: 'Premium Account',     inline: true },
      { name: 'Status',  value: '✅ Check your DMs!',  inline: true },
      { name: 'Remaining Premium', value: `${remaining}`, inline: true },
    )
    .setFooter({ text: 'R6 Generator' })
    .setTimestamp();
}

// ============================================================
//  CLIENT
// ============================================================
const client = new Client({
  intents: [GatewayIntentBits.Guilds, GatewayIntentBits.GuildMessages, GatewayIntentBits.DirectMessages]
});

// ============================================================
//  COMMANDS
// ============================================================
const commands = [
  new SlashCommandBuilder()
    .setName('addaccount')
    .setDescription('[Owner] Add a single account to the list')
    .addStringOption(o => o.setName('account').setDescription('email:pass | field | field ...').setRequired(true)),

  new SlashCommandBuilder()
    .setName('addaccounts')
    .setDescription('[Owner] Bulk add accounts (one per line)')
    .addStringOption(o => o.setName('accounts').setDescription('Paste multiple accounts separated by newlines').setRequired(true)),

  new SlashCommandBuilder()
    .setName('addpremium')
    .setDescription('[Owner] Grant premium to a user')
    .addUserOption(o => o.setName('user').setDescription('User to add').setRequired(true)),

  new SlashCommandBuilder()
    .setName('removepremium')
    .setDescription('[Owner] Remove premium from a user')
    .addUserOption(o => o.setName('user').setDescription('User to remove').setRequired(true)),

  new SlashCommandBuilder()
    .setName('gen')
    .setDescription('Generate a premium R6 account (premium only)'),

  new SlashCommandBuilder()
    .setName('stock')
    .setDescription('Check current account stock'),

  new SlashCommandBuilder()
    .setName('premiumlist')
    .setDescription('[Owner] View all premium users'),
].map(c => c.toJSON());

// ============================================================
//  REGISTER COMMANDS
// ============================================================
async function registerCommands(token, clientId) {
  const rest = new REST({ version: '10' }).setToken(token);
  try {
    console.log('Registering slash commands...');
    await rest.put(Routes.applicationCommands(clientId), { body: commands });
    console.log('✅ Commands registered globally');
  } catch (err) {
    console.error('Failed to register commands:', err);
  }
}

// ============================================================
//  INTERACTION HANDLER
// ============================================================
client.on('interactionCreate', async interaction => {
  if (!interaction.isChatInputCommand()) return;
  const { commandName, user } = interaction;
  const isOwner = user.id === OWNER_ID;

  // ---- /addaccount ----------------------------------------
  if (commandName === 'addaccount') {
    if (!isOwner) return interaction.reply({ content: '❌ Owner only.', ephemeral: true });
    const line     = interaction.options.getString('account');
    const accounts = getAccounts();
    accounts.push(parseAccount(line));
    saveAccounts(accounts);
    return interaction.reply({ content: `✅ Account added. Total: **${accounts.length}**`, ephemeral: true });
  }

  // ---- /addaccounts (bulk) --------------------------------
  if (commandName === 'addaccounts') {
    if (!isOwner) return interaction.reply({ content: '❌ Owner only.', ephemeral: true });
    const raw      = interaction.options.getString('accounts');
    const lines    = raw.split('\n').map(l => l.trim()).filter(Boolean);
    const accounts = getAccounts();
    let added = 0;
    for (const line of lines) { accounts.push(parseAccount(line)); added++; }
    saveAccounts(accounts);
    return interaction.reply({ content: `✅ Added **${added}** accounts. Total: **${accounts.length}**`, ephemeral: true });
  }

  // ---- /addpremium ----------------------------------------
  if (commandName === 'addpremium') {
    if (!isOwner) return interaction.reply({ content: '❌ Owner only.', ephemeral: true });
    const target  = interaction.options.getUser('user');
    const premium = getPremium();
    if (premium.includes(target.id)) return interaction.reply({ content: `ℹ️ ${target.tag} already has premium.`, ephemeral: true });
    premium.push(target.id);
    savePremium(premium);
    return interaction.reply({ content: `✅ **${target.tag}** has been granted premium!`, ephemeral: true });
  }

  // ---- /removepremium -------------------------------------
  if (commandName === 'removepremium') {
    if (!isOwner) return interaction.reply({ content: '❌ Owner only.', ephemeral: true });
    const target  = interaction.options.getUser('user');
    let premium   = getPremium();
    if (!premium.includes(target.id)) return interaction.reply({ content: `ℹ️ ${target.tag} doesn't have premium.`, ephemeral: true });
    premium = premium.filter(id => id !== target.id);
    savePremium(premium);
    return interaction.reply({ content: `✅ **${target.tag}**'s premium has been removed.`, ephemeral: true });
  }

  // ---- /premiumlist ---------------------------------------
  if (commandName === 'premiumlist') {
    if (!isOwner) return interaction.reply({ content: '❌ Owner only.', ephemeral: true });
    const premium = getPremium();
    if (!premium.length) return interaction.reply({ content: 'No premium users.', ephemeral: true });
    const list = premium.map((id, i) => `${i + 1}. <@${id}>`).join('\n');
    const embed = new EmbedBuilder()
      .setColor(0xFFD700)
      .setTitle('👑 Premium Users')
      .setDescription(list)
      .setFooter({ text: `Total: ${premium.length}` });
    return interaction.reply({ embeds: [embed], ephemeral: true });
  }

  // ---- /stock ---------------------------------------------
  if (commandName === 'stock') {
    const accounts = getAccounts();
    const embed = new EmbedBuilder()
      .setColor(0x00BFFF)
      .setTitle('📦 Account Stock')
      .addFields({ name: 'Premium Accounts', value: `${accounts.length}`, inline: true })
      .setTimestamp();
    return interaction.reply({ embeds: [embed] });
  }

  // ---- /gen -----------------------------------------------
  if (commandName === 'gen') {
    const premium  = getPremium();
    const isOwnerGen = isOwner;
    const hasPremium = premium.includes(user.id) || isOwnerGen;

    if (!hasPremium) {
      const embed = new EmbedBuilder()
        .setColor(0xFF4444)
        .setTitle('❌ No Premium Access')
        .setDescription('Please open a ticket to purchase premium.\nOnce premium has been purchased, you can generate an account.')
        .setThumbnail(user.displayAvatarURL({ dynamic: true }))
        .setFooter({ text: 'R6 Generator' });
      return interaction.reply({ embeds: [embed], ephemeral: true });
    }

    const accounts = getAccounts();
    if (!accounts.length) {
      return interaction.reply({ content: '❌ No accounts in stock right now. Check back soon!', ephemeral: true });
    }

    // Pop one account
    const acc = accounts.shift();
    saveAccounts(accounts);
    const remaining = accounts.length;

    // Send DM
    try {
      const dmEmbed = buildDMEmbed(acc, remaining, user);
      await user.send({ embeds: [dmEmbed] });
    } catch {
      return interaction.reply({ content: '❌ I couldn\'t DM you! Please enable DMs from server members and try again.', ephemeral: true });
    }

    // Reply in channel
    const channelEmbed = buildChannelEmbed(user, remaining);
    return interaction.reply({ embeds: [channelEmbed] });
  }
});

// ============================================================
//  READY
// ============================================================
client.once('ready', async () => {
  console.log(`✅ Logged in as ${client.user.tag}`);
  await registerCommands(process.env.DISCORD_TOKEN, client.user.id);
});

client.login(process.env.DISCORD_TOKEN);
