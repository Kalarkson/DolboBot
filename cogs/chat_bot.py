import disnake
from disnake.ext import commands
from disnake import Embed, SelectOption, TextInputStyle, ChannelType, ButtonStyle
from disnake.ui import View, RoleSelect, UserSelect, ChannelSelect, TextInput, Button

from config import *
from audit import audit

import asyncio, ollama, json, os, random


class DiscordResponse:
  def __init__(self, message):
    self.message = message
    self.channel = message.channel

    self.r = None

  async def write(self, message, s, end=''):

    value = self.sanitize(s)
    if not value:
      value = '*Мне нечего сказать.*'

    i = 0
    if len(value) >= 2000:
      done = False
      referenced = False
      message_remaining = value

      while not done:
        i += 1
        if i > 10:
          break
        
        split_index = message_remaining.rfind('\n', 0, 2000)

        if split_index == -1:
            split_index = 2000
            
            if len(message_remaining) <= 2000:
              split_index = len(message_remaining)
            
        chunk_to_send = message_remaining[:split_index]

        if len(chunk_to_send) == 0 and len(message_remaining) > 0 and len(message_remaining) <= 2000:
          chunk_to_send = message_remaining
          done = True
        if len(chunk_to_send) == 0:
          done = True
          continue
        
        if not referenced:
          self.r = await self.channel.send(chunk_to_send, reference=message)
          referenced = True
        else:
          await self.channel.send(chunk_to_send)

        message_remaining = message_remaining[split_index:]

        if len(message_remaining) == 0:
            done = True
            break
            
        await asyncio.sleep(0.5)
        
    else:
        await self.channel.send(value, reference=message)


class FileStorage:
    def __init__(self, directory):
        self.directory = directory

    async def load_channel(self, channel_id):
        file_path = os.path.join(self.directory, f"channel_{channel_id}.json")
        if os.path.exists(file_path):
            with open(file_path, "r") as f:
                return json.load(f)
        return []

    async def save_message(self, channel_id, message, role):
        file_path = os.path.join(self.directory, f"channel_{channel_id}.json")
        messages = await self.load_channel(channel_id)
        messages.append({"role": role, "content": message})
        with open(file_path, "w") as f:
            json.dump(messages, f)

    async def flush_channel(self, channel_id):
        file_path = os.path.join(self.directory, f"channel_{channel_id}.json")
        if os.path.exists(file_path):
            os.remove(file_path)
            

class ChatBot(commands.Cog):
    def __init__(self, bot=commands.Bot):
        self.bot = bot
        self.storage = FileStorage("channels")
        self.ollama_client = ollama.AsyncClient()
        
    async def load_channel(self, channel_id):
        return await self.storage.load_channel(channel_id)

    async def save_message(self, channel_id, message, role):
        await self.storage.save_message(channel_id, f"{message}", role)

    async def flush_channel(self, channel_id):
        await self.storage.flush_channel(channel_id)
        
    async def thinking(self, message, timeout=999):
        try:
            async with message.channel.typing():
                await asyncio.sleep(timeout)
        except Exception:
            pass

    async def chat(self, channel_id):
        try:
            local_messages = await self.load_channel(channel_id)
            
            response_message = ''
            data = await self.ollama_client.chat(model=OLLAMA.model, keep_alive=-1, stream=False, messages=local_messages, options={'num_ctx': BOT.ctx, "temperature": OLLAMA.temperature})
            try:
                response_message = data['message']['content']
                await self.save_message(channel_id, response_message, 'assistant')      
            except Exception as e:
                audit.error(f'Ошибка сохранения ответа: {e}')
                return 'Извините, в данный момент я не могу ответить...'
                
            return response_message
        except Exception as e:
            audit.error(f'Ошибка генерации ответа: {e}')
            return 'Извините, в данный момент я не могу ответить...'
        
    def message(self, message, content=''):
        try:
            said = "said"
            if message.reference:
                said = f'ответил на {message.reference.message_id}'
                
            chat_name = "этот чат"
            try:
                chat_name = message.channel.name
            except Exception as e:
                pass
            
            return f'**({message.id}) в {message.created_at.strftime("%Y-%m-%d %H:%M:%S")} {message.author.name}({message.author.id}) {said} в {chat_name}**: {content}'
        except Exception as e:
            audit.error(f'Ошибка генерации ответа: {e}')
            return ''
        
    @commands.Cog.listener()
    async def on_ready(self):
        audit.info('Модуль {} активирован'.format(self.__class__.__name__))
        print(f"Модуль {self.__class__.__name__} активирован")
        
    @commands.Cog.listener(disnake.Event.message)
    @commands.guild_only()
    async def chat_bot(self, message):
        string_channel_id = str(message.channel.id)
        if self.bot.user == message.author:
            return
        
        my_mention = self.bot.user.mentioned_in(message)
        if my_mention or (not my_mention and random.random() < BOT.no_mention_prob):
            content = message.content.replace(f'<@{self.bot.user.id}>', BOT.name.title()).strip()
            if not content:
                return
            
            if content == 'RESET' and str(message.author.id) == self.admin_id:
                await self.flush_channel(str(message.channel.id))
                audit.info('Сброс чата администратором')
                await self.save_message(string_channel_id, '*Вы присоединились к чату!' + str(message.channel.guild.name) + '.*', 'assistant')
                return
            else:
                channel = message.channel

                audit.info(f'Генерация ответа на сообщение {message.id} в канале {channel.id}')
                
                response = DiscordResponse(message)
                
                task = asyncio.create_task(self.thinking(message))
                
                try:
                    await self.save_message(string_channel_id, self.message(message, content), 'user')
                    
                    response = await self.chat(string_channel_id)
                    
                    await message.channel.send(response)
                    await asyncio.sleep(0.5)
                except Exception as e:
                    audit.error(f'Ошибка отправки ответа: {e}')
                finally:
                    task.cancel()
        else:
            await self.save_message(str(message.channel.id), self.message(message, message.content), 'user')

def setup(bot: commands.Bot):
    bot.add_cog(ChatBot(bot))